"""Rebuild identified manifests from external data, retaining provider test partitions."""

from __future__ import annotations

import json
import stat
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from conformal_pathways.data.loaders import load_samples_from_csv
from conformal_pathways.features.cache import input_identity, sha256_file
from conformal_pathways.ingest.idrid import IDRiDBuilder
from conformal_pathways.ingest.rimone import RIMONEBuilder

from .provenance import digest, verify_protocol, write_json

IDRID_TRAIN = "B. Disease Grading/2. Groundtruths/a_IDRiD_Disease_Grading_Training_Labels.csv"
IDRID_TEST = "B. Disease Grading/2. Groundtruths/b_IDRiD_Disease_Grading_Testing_Labels.csv"


def resolve_image_duplicates(samples, identities, labels, policy="reject"):
    """Resolve exact bytes before splitting; never adjudicate conflicting labels."""
    if policy not in {"reject", "exclude_conflicts_keep_lexicographic_v1"}:
        raise ValueError("unknown image duplicate policy")
    sample_ids = {s.sample_id for s in samples}
    if (
        len(sample_ids) != len(samples)
        or len(identities) != len(samples)
        or sample_ids != {r["sample_id"] for r in identities}
    ):
        raise ValueError("sample and image identities do not match")
    groups = defaultdict(list)
    for row in identities:
        groups[row["image_sha256"]].append(row["sample_id"])
    exclusions = []
    for image_hash, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        if policy == "reject":
            raise ValueError(
                "duplicate image bytes; resolve before treating images as separate units"
            )
        if any(sid not in labels or any(v is None for v in labels[sid]) for sid in members):
            raise ValueError("duplicate resolution requires complete source labels")
        conflict = len({tuple(labels[sid]) for sid in members}) > 1
        # Qualified IDs order test before train; no test image is moved into training.
        removed = sorted(members) if conflict else sorted(members)[1:]
        for sid in removed:
            exclusions.append(
                {
                    "sample_id": sid,
                    "image_sha256": image_hash,
                    "reason": "conflicting_source_labels"
                    if conflict
                    else "redundant_agreeing_duplicate",
                }
            )
    exclusions.sort(key=lambda row: row["sample_id"])
    removed_ids = {row["sample_id"] for row in exclusions}
    return (
        [s for s in samples if s.sample_id not in removed_ids],
        [r for r in identities if r["sample_id"] not in removed_ids],
        exclusions,
    )


def idrid_source_labels(root):
    """Retain full source DME grades for conflict detection, before proxy mapping."""
    labels = {}
    for partition, relative in (("train", IDRID_TRAIN), ("test", IDRID_TEST)):
        frame = pd.read_csv(Path(root) / relative)
        frame.columns = frame.columns.str.strip()
        for row in frame.to_dict("records"):
            sid = f"idrid/{partition}/{str(row['Image name']).strip()}"
            labels[sid] = (int(row["Retinopathy grade"]), int(row["Risk of macular edema"]))
    return labels


def prepare_dataset(name, data_root, output, config):
    root, out = Path(data_root) / name, Path(output)
    image_root = root / (
        "B. Disease Grading/1. Original Images" if name == "idrid" else "partitioned_randomly"
    )
    assert_local_images(image_root)
    manifest = out / f"{name}.csv"
    if name == "idrid":
        annotations = {
            "idrid_train": sha256_file(root / IDRID_TRAIN),
            "idrid_test": sha256_file(root / IDRID_TEST),
        }
        if annotations != config["annotation_sha256"]:
            raise ValueError("IDRiD annotation files differ from the frozen input identity")
        IDRiDBuilder().build_manifest(root, manifest, testing_labels_csv=IDRID_TEST)
        workflow, label, classes = "dr_workflow", "dr_severity", list(range(5))
    elif name == "rimone":
        RIMONEBuilder().build_manifest(root, manifest, base_dir="partitioned_randomly")
        workflow, label, classes = "glaucoma_workflow", "glaucoma_risk", ["low", "high"]
        annotations = {"label_source": "provider_directory_classes"}
    else:
        raise ValueError("unsupported frozen dataset")
    samples = load_samples_from_csv(
        str(manifest),
        None,
        label_cols=["dr_severity", "dme_positive", "glaucoma_risk"],
        meta_cols=["patient_id", "eye_id", "group_provenance"],
    )
    counts = dict(Counter(s.meta["split_hint"] for s in samples))
    if counts != config["expected_partitions"][name]:
        raise ValueError(f"{name}: missing/extra images or changed official partition")
    identities = input_identity(manifest, root)
    raw_images_sha256 = digest(identities)
    raw_manifest_sha256 = sha256_file(manifest)
    policy = config.get("duplicate_policy", {}).get(name, "reject")
    if policy != "reject" and name != "idrid":
        raise ValueError("only the IDRiD amendment permits duplicate exclusions")
    samples, identities, exclusions = resolve_image_duplicates(
        samples, identities, idrid_source_labels(root) if policy != "reject" else {}, policy
    )
    analysis_counts = dict(Counter(s.meta["split_hint"] for s in samples))
    expected_analysis = config.get("expected_analysis_partitions", config["expected_partitions"])
    if analysis_counts != expected_analysis[name]:
        raise ValueError(f"{name}: analysis partition counts differ from the frozen protocol")
    exclusion_counts = dict(Counter(r["reason"] for r in exclusions))
    if exclusion_counts != config.get("expected_exclusions", {}).get(name, {}):
        raise ValueError(f"{name}: exclusion counts differ from the frozen protocol")
    if exclusions:
        frame = pd.read_csv(manifest, dtype=str, keep_default_na=False)
        frame[frame["sample_id"].isin({s.sample_id for s in samples})].to_csv(manifest, index=False)
    write_json(out / f"{name}.exclusions.json", exclusions)
    audit = {
        "dataset": name,
        "workflow": workflow,
        "n_images": len(samples),
        "provider_partition_counts": counts,
        "analysis_partition_counts": analysis_counts,
        "raw_manifest_sha256": raw_manifest_sha256,
        "raw_images_sha256": raw_images_sha256,
        "duplicate_policy": policy,
        "exclusion_counts": exclusion_counts,
        "exclusions_sha256": digest(exclusions),
        "manifest_sha256": sha256_file(manifest),
        "images_sha256": digest(identities),
        "annotations": annotations,
        "entry_observations": [],
        "group_identity": "sample_id_fallback; patient_linkage_unverified",
        "inference_scope": "descriptive_filtered_provider_test_image_surrogate_metrics"
        if exclusions
        else "descriptive_official_test_image_surrogate_metrics",
        "label_interpretation": "DME risk grade > 0 proxy; not an OCT response"
        if name == "idrid"
        else "disease class mapped to toy low/high; not a longitudinal risk estimate",
    }
    write_json(out / f"{name}.images.json", identities)
    write_json(out / f"{name}.audit.json", audit)
    return samples, manifest, root, workflow, label, classes, audit


def verify_checkpoint(config):
    import torch
    from torchvision.models import ResNet50_Weights

    weights = ResNet50_Weights.IMAGENET1K_V2
    if config["weights"] != weights.name:
        raise ValueError("unsupported checkpoint identity")
    path = Path(torch.hub.get_dir()) / "checkpoints" / Path(urlparse(weights.url).path).name
    if not path.exists():
        weights.get_state_dict(progress=False, check_hash=True)
    actual = sha256_file(path)
    if actual != config["checkpoint_sha256"]:
        raise ValueError("pretrained checkpoint SHA-256 mismatch")
    return {"name": weights.name, "url": weights.url, "sha256": actual}


def assert_local_images(root):
    # SF_DATALESS identifies macOS File Provider placeholders. Hashing one can
    # otherwise block indefinitely while the OS tries to fetch its content.
    flag = getattr(stat, "SF_DATALESS", 0x40000000)
    placeholders = [
        p
        for p in Path(root).rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"} and getattr(p.stat(), "st_flags", 0) & flag
    ]
    if placeholders:
        raise RuntimeError(
            f"{len(placeholders)} cloud-only image files; make the dataset available offline first"
        )


def audit_input_lock(config_path, data_root):
    config, frozen = verify_protocol(config_path)
    destination = Path(config_path).resolve().parent / config["real"]["input_lock"]
    if destination.exists():
        raise ValueError(
            "input lock already exists; preserve it and use a new protocol for changed inputs"
        )
    audits = {}
    with tempfile.TemporaryDirectory(prefix="conformal-input-audit-") as temporary:
        for name in config["real"]["datasets"]:
            *_, audit = prepare_dataset(name, data_root, temporary, config["real"])
            audits[name] = audit
    record = {
        "schema_version": 1,
        "protocol_sha256": frozen["protocol_sha256"],
        "source_sha256": frozen["source_sha256"],
        "dataset_audits": audits,
        "images_sha256": {name: value["images_sha256"] for name, value in audits.items()},
    }
    write_json(destination, record)
    return record


def load_input_lock(config_path, config, frozen):
    path = Path(config_path).resolve().parent / config["real"]["input_lock"]
    if not path.is_file():
        raise ValueError(
            "real-data inputs have not been sealed; run audit-data after making all images available offline"
        )
    record = json.loads(path.read_text())
    if (
        record["protocol_sha256"] != frozen["protocol_sha256"]
        or record["source_sha256"] != frozen["source_sha256"]
    ):
        raise ValueError("input lock belongs to a different protocol or source revision")
    if set(record["images_sha256"]) != set(config["real"]["datasets"]):
        raise ValueError("input lock omits a required dataset")
    return record
