"""Pre-outcome input-policy checks, using invented file identities and grades."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from conformal_pathways.benchmarks.datasets import (
    IDRID_TEST,
    IDRID_TRAIN,
    prepare_dataset,
    resolve_image_duplicates,
)
from conformal_pathways.benchmarks.provenance import source_files
from conformal_pathways.features.cache import sha256_file

POLICY = "exclude_conflicts_keep_lexicographic_v1"
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicts_remove_every_copy_and_agreement_keeps_one_without_moving_partitions(reverse):
    rows = [
        ("idrid/train/A", "conflict", (2, 1)),
        ("idrid/test/B", "conflict", (2, 2)),  # Same binary DME, different source grade.
        ("idrid/train/C", "conflict", (2, 1)),
        ("idrid/train/D", "agree", (1, 0)),
        ("idrid/test/E", "agree", (1, 0)),
        ("idrid/train/F", "unique", (4, 2)),
    ]
    if reverse:
        rows.reverse()
    samples = [SimpleNamespace(sample_id=sid) for sid, _, _ in rows]
    identities = [{"sample_id": sid, "image_sha256": sha} for sid, sha, _ in rows]
    labels = {sid: label for sid, _, label in rows}
    retained, identities, removed = resolve_image_duplicates(samples, identities, labels, POLICY)
    assert {s.sample_id for s in retained} == {"idrid/test/E", "idrid/train/F"}
    assert len(identities) == 2
    assert [r["sample_id"] for r in removed] == [
        "idrid/test/B",
        "idrid/train/A",
        "idrid/train/C",
        "idrid/train/D",
    ]
    assert [r["reason"] for r in removed] == ["conflicting_source_labels"] * 3 + [
        "redundant_agreeing_duplicate"
    ]


@pytest.mark.parametrize(
    "policy,labels,match",
    [
        ("reject", {}, "duplicate image"),
        ("unknown", {}, "unknown"),
        (POLICY, {"a": (0, 0)}, "complete source labels"),
        (POLICY, {"a": (0, None), "b": (0, 0)}, "complete source labels"),
    ],
)
def test_duplicate_resolution_fails_closed(policy, labels, match):
    samples = [SimpleNamespace(sample_id=s) for s in ("a", "b")]
    identities = [{"sample_id": s, "image_sha256": "same"} for s in ("a", "b")]
    with pytest.raises(ValueError, match=match):
        resolve_image_duplicates(samples, identities, labels, policy)


def test_duplicate_identity_rows_are_rejected():
    sample = SimpleNamespace(sample_id="a")
    identity = {"sample_id": "a", "image_sha256": "same"}
    with pytest.raises(ValueError, match="identities"):
        resolve_image_duplicates([sample], [identity, identity], {"a": (0, 0)}, POLICY)


def make_idrid_fixture(tmp_path):
    root = tmp_path / "data/idrid"
    rows = {
        "train": [
            ("A", 0, 0, b"conflict"),
            ("B", 3, 0, b"conflict"),
            ("C", 2, 1, b"agree"),
            ("D", 2, 1, b"agree"),
            ("E", 4, 2, b"unique-train"),
        ],
        "test": [("F", 0, 0, b"unique-test")],
    }
    images = {}
    for partition, values in rows.items():
        directory = "a. Training Set" if partition == "train" else "b. Testing Set"
        for sid, _, _, content in values:
            image = root / "B. Disease Grading/1. Original Images" / directory / f"{sid}.jpg"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(content)
            images[sid] = image
        annotations = root / (IDRID_TRAIN if partition == "train" else IDRID_TEST)
        annotations.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [v[:3] for v in values],
            columns=["Image name", "Retinopathy grade", "Risk of macular edema"],
        ).to_csv(annotations, index=False)
    config = {
        "annotation_sha256": {
            "idrid_train": sha256_file(root / IDRID_TRAIN),
            "idrid_test": sha256_file(root / IDRID_TEST),
        },
        "expected_partitions": {"idrid": {"train": 5, "test": 1}},
        "expected_analysis_partitions": {"idrid": {"train": 2, "test": 1}},
        "duplicate_policy": {"idrid": POLICY},
        "expected_exclusions": {
            "idrid": {"conflicting_source_labels": 2, "redundant_agreeing_duplicate": 1}
        },
    }
    return root.parent, images, config


def test_manifest_only_exclusions_preserve_source_and_seal_excluded_bytes(tmp_path):
    data, images, config = make_idrid_fixture(tmp_path)
    before = {p: sha256_file(p) for p in data.rglob("*") if p.is_file()}
    samples, manifest, *_, audit = prepare_dataset("idrid", data, tmp_path / "first", config)
    assert {s.sample_id for s in samples} == {"idrid/train/C", "idrid/train/E", "idrid/test/F"}
    assert len(pd.read_csv(manifest)) == 3
    assert before == {p: sha256_file(p) for p in before}
    # Change only the two excluded copies, preserving their conflicting duplicate group.
    images["A"].write_bytes(b"changed-excluded-group")
    images["B"].write_bytes(b"changed-excluded-group")
    *_, changed = prepare_dataset("idrid", data, tmp_path / "second", config)
    assert changed["images_sha256"] == audit["images_sha256"]
    assert changed["manifest_sha256"] == audit["manifest_sha256"]
    assert changed["raw_images_sha256"] != audit["raw_images_sha256"]
    assert changed["exclusions_sha256"] != audit["exclusions_sha256"]


def test_unexpected_analysis_count_fails(tmp_path):
    data, _, config = make_idrid_fixture(tmp_path)
    config["expected_analysis_partitions"]["idrid"]["train"] = 3
    with pytest.raises(ValueError, match="analysis partition counts"):
        prepare_dataset("idrid", data, tmp_path / "output", config)


def test_real_run_checks_raw_audit_before_feature_extraction(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from conformal_pathways.benchmarks import datasets, runner
    from conformal_pathways.features import extract_embeddings

    data, _, config = make_idrid_fixture(tmp_path)
    *_, audit = prepare_dataset("idrid", data, tmp_path / "seal", config)
    sealed = {**audit, "raw_images_sha256": "changed-excluded-source"}
    config.update(torch_threads=2, datasets=["idrid"])
    monkeypatch.setattr(datasets, "verify_checkpoint", lambda _: {})

    def must_not_extract(*args, **kwargs):
        pytest.fail("feature extraction must not begin with changed sealed inputs")

    monkeypatch.setattr(extract_embeddings, "extract_embeddings_from_manifest", must_not_extract)
    with pytest.raises(ValueError, match="raw inputs"):
        runner._real(
            {"real": config}, tmp_path / "run", data, {"dataset_audits": {"idrid": sealed}}
        )


def test_amendment_is_hashed_and_cannot_escape_docs(tmp_path):
    config = json.loads((ROOT / "experiments/batch3-v2.json").read_text())
    path = tmp_path / "experiments/config.json"
    path.parent.mkdir()
    (tmp_path / "docs").mkdir()
    for name in ("pyproject.toml", "uv.lock", "docs/experiment-protocol.md", "docs/amendment.md"):
        (tmp_path / name).write_text("fixture")
    config["protocol_documents"] = ["docs/experiment-protocol.md", "docs/amendment.md"]
    path.write_text(json.dumps(config))
    before = source_files(tmp_path, path)
    (tmp_path / "docs/amendment.md").write_text("changed")
    assert source_files(tmp_path, path)["docs/amendment.md"] != before["docs/amendment.md"]
    config["protocol_documents"] = ["../outside.md"]
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="inside docs"):
        source_files(tmp_path, path)


@pytest.mark.parametrize(
    "limit,program,expected",
    [
        (8, "raise SystemExit(3)", None),
        (0.000001, "import time; time.sleep(20)", "process_group_rss_limit"),
    ],
)
def test_resource_guard_preserves_failure_and_terminates_own_command(
    tmp_path, limit, program, expected
):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_monitored.py"),
            "--record",
            str(tmp_path / "memory.json"),
            "--log",
            str(tmp_path / "run.log"),
            "--interval",
            "0.02",
            "--max-rss-gib",
            str(limit),
            "--",
            sys.executable,
            "-c",
            program,
        ],
        capture_output=True,
        timeout=15,
    )
    record = json.loads((tmp_path / "memory.json").read_text())
    assert result.returncode != 0 and record["status"] == "failed"
    assert record["stop_reason"] == expected
    if expected is None:
        assert record["exit_code"] == 3
