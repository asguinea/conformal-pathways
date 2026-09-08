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
        "Image name, Retinopathy grade, Risk of macular edema,\nIDRiD_001,2,1,\n",
        encoding="utf-8",
    )

    test_csv = labels_dir / "testing.csv"
    test_csv.write_text("Image name,Retinopathy grade,Risk of macular edema\nIDRiD_002,0,0\n")
    builder = IDRiDBuilder()
    result = builder.build_manifest(
        root=root, out_csv=root / "manifest.csv", dry_run=True, testing_labels_csv=test_csv
    )
    manifest = result["df"]

    assert len(manifest) == 2
    assert set(["sample_id", "dr_severity", "dme_positive"]).issubset(manifest.columns)

    row1 = manifest.loc[manifest["sample_id"] == "idrid/train/IDRiD_001"].iloc[0]
    row2 = manifest.loc[manifest["sample_id"] == "idrid/test/IDRiD_002"].iloc[0]
    assert row1["dr_severity"] == 2
    assert bool(row1["dme_positive"]) is True
    assert bool(row2["dme_positive"]) is False

    assert row1["split_hint"] == "train"
    assert row2["split_hint"] == "test"
    assert manifest["patient_id"].isna().all()


def test_idrid_rejects_fractional_risk_grade(tmp_path):
    import pytest

    (tmp_path / "case.jpg").write_bytes(b"image")
    labels = tmp_path / "labels.csv"
    labels.write_text("Image name,Retinopathy grade,Risk of macular edema\ncase,2,1.5\n")
    with pytest.raises(ValueError, match="invalid"):
        IDRiDBuilder().build_manifest(
            tmp_path,
            tmp_path / "out.csv",
            training_images_dir=".",
            training_labels_csv=labels,
            dry_run=True,
        )


def test_idrid_reused_image_number_across_partitions_is_namespaced(tmp_path):
    for split in ("train", "test"):
        (tmp_path / split).mkdir()
        (tmp_path / split / "IDRiD_001.jpg").write_bytes(split.encode())
        (tmp_path / f"{split}.csv").write_text(
            "Image name,Retinopathy grade,Risk of macular edema\nIDRiD_001,2,0\n"
        )
    result = IDRiDBuilder().build_manifest(
        tmp_path,
        tmp_path / "out.csv",
        dry_run=True,
        training_images_dir="train",
        testing_images_dir="test",
        training_labels_csv="train.csv",
        testing_labels_csv="test.csv",
    )
    assert set(result["df"]["sample_id"]) == {"idrid/train/IDRiD_001", "idrid/test/IDRiD_001"}
    assert result["df"]["source_sample_id"].tolist() == ["IDRiD_001", "IDRiD_001"]
