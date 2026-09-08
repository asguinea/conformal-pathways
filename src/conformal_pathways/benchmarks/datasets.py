"""Rebuild identified manifests from external data, retaining provider test partitions."""

from __future__ import annotations

import json
import stat
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from conformal_pathways.data.loaders import load_samples_from_csv
from conformal_pathways.features.cache import input_identity, sha256_file
from conformal_pathways.ingest.idrid import IDRiDBuilder
from conformal_pathways.ingest.rimone import RIMONEBuilder

from .provenance import digest, verify_protocol, write_json

IDRID_TRAIN = "B. Disease Grading/2. Groundtruths/a_IDRiD_Disease_Grading_Training_Labels.csv"
IDRID_TEST = "B. Disease Grading/2. Groundtruths/b_IDRiD_Disease_Grading_Testing_Labels.csv"


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
    hashes = [r["image_sha256"] for r in identities]
    if len(set(hashes)) != len(hashes):
        raise ValueError("duplicate image bytes; resolve before treating images as separate units")
    audit = {
        "dataset": name,
        "workflow": workflow,
        "n_images": len(samples),
        "provider_partition_counts": counts,
        "manifest_sha256": sha256_file(manifest),
        "images_sha256": digest(identities),
        "annotations": annotations,
        "entry_observations": [],
        "group_identity": "sample_id_fallback; patient_linkage_unverified",
        "inference_scope": "descriptive_official_test_image_surrogate_metrics",
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
