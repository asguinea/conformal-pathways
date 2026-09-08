from __future__ import annotations

from conformal_pathways.ingest.idrid import IDRiDBuilder


def test_idrid_builder_manifest_and_dme_mapping(tmp_path) -> None:
    root = tmp_path
    train_images = root / "B. Disease Grading/1. Original Images/a. Training Set"
    test_images = root / "B. Disease Grading/1. Original Images/b. Testing Set"
    labels_dir = root / "B. Disease Grading/2. Groundtruths"
    train_images.mkdir(parents=True)
    test_images.mkdir(parents=True)
    labels_dir.mkdir(parents=True)

    (train_images / "IDRiD_001.jpg").write_bytes(b"img")
    (test_images / "IDRiD_002.png").write_bytes(b"img")

    labels_csv = labels_dir / "a_IDRiD_Disease_Grading_Training_Labels.csv"
    labels_csv.write_text(
        "Image name, Retinopathy grade, Risk of macular edema,\n"
        "IDRiD_001,2,1,\n"
        "IDRiD_002,0,0,\n",
        encoding="utf-8",
    )

    builder = IDRiDBuilder()
    result = builder.build_manifest(root=root, out_csv=root / "manifest.csv", dry_run=True)
    manifest = result["df"]

    assert len(manifest) == 2
    assert set(["sample_id", "dr_severity", "dme_positive"]).issubset(manifest.columns)

    row1 = manifest.loc[manifest["sample_id"] == "IDRiD_001"].iloc[0]
    row2 = manifest.loc[manifest["sample_id"] == "IDRiD_002"].iloc[0]
    assert row1["dr_severity"] == 2
    assert bool(row1["dme_positive"]) is True
    assert bool(row2["dme_positive"]) is False
