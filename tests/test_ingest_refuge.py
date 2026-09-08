from __future__ import annotations

from conformal_pathways.ingest.refuge import REFUGEBuilder


def test_refuge_builder_manifest(tmp_path) -> None:
    root = tmp_path
    glaucoma_dir = root / "Training400/Glaucoma"
    non_dir = root / "Training400/Non-Glaucoma"
    glaucoma_dir.mkdir(parents=True)
    non_dir.mkdir(parents=True)

    (glaucoma_dir / "g1.png").write_bytes(b"img")
    (non_dir / "n1.jpg").write_bytes(b"img")

    builder = REFUGEBuilder()
    result = builder.build_manifest(root=root, out_csv=root / "manifest.csv", dry_run=True)
    manifest = result["df"]

    assert len(manifest) == 2
    assert set(["sample_id", "glaucoma_risk", "dataset_source"]).issubset(manifest.columns)

    risk_map = dict(zip(manifest["sample_id"], manifest["glaucoma_risk"]))
    assert risk_map["g1"] == "high"
    assert risk_map["n1"] == "low"
