from __future__ import annotations

from conformal_pathways.ingest.rimone import RIMONEBuilder


def test_rimone_builder_manifest(tmp_path) -> None:
    root = tmp_path
    train_glaucoma = root / "partitioned_randomly/training_set/glaucoma"
    train_normal = root / "partitioned_randomly/training_set/normal"
    test_glaucoma = root / "partitioned_randomly/test_set/glaucoma"
    test_normal = root / "partitioned_randomly/test_set/normal"

    train_glaucoma.mkdir(parents=True)
    train_normal.mkdir(parents=True)
    test_glaucoma.mkdir(parents=True)
    test_normal.mkdir(parents=True)

    (train_glaucoma / "tg1.png").write_bytes(b"img")
    (train_normal / "tn1.jpg").write_bytes(b"img")
    (test_glaucoma / "eg1.bmp").write_bytes(b"img")
    (test_normal / "en1.png").write_bytes(b"img")

    builder = RIMONEBuilder()
    result = builder.build_manifest(root=root, out_csv=root / "manifest.csv", dry_run=True)
    manifest = result["df"]

    assert len(manifest) == 4
    assert set(["glaucoma_risk", "split_hint", "dataset_source"]).issubset(manifest.columns)

    split_map = dict(zip(manifest["sample_id"], manifest["split_hint"]))
    risk_map = dict(zip(manifest["sample_id"], manifest["glaucoma_risk"]))

    assert split_map["tg1"] == "train"
    assert split_map["en1"] == "test"
    assert risk_map["tg1"] == "high"
    assert risk_map["tn1"] == "low"
