from __future__ import annotations

import pandas as pd

from conformal_pathways.ingest.eyepacs import EyePACSBuilder


def test_eyepacs_builder_manifest(tmp_path) -> None:
    root = tmp_path
    train_dir = root / "train"
    train_dir.mkdir(parents=True)

    (train_dir / "10_left.jpeg").write_bytes(b"img")
    (train_dir / "10_right.jpg").write_bytes(b"img")

    labels_df = pd.DataFrame(
        [
            {"image": "10_left", "level": 2},
            {"image": "10_right", "level": 1},
            {"image": "missing_left", "level": 0},
        ]
    )
    labels_df.to_csv(root / "trainLabels.csv", index=False)

    builder = EyePACSBuilder()
    result = builder.build_manifest(root=root, out_csv=root / "manifest.csv", dry_run=True)
    manifest = result["df"]

    assert len(manifest) == 2
    assert set(["sample_id", "image_path", "dataset_source"]).issubset(manifest.columns)
    assert set(["dr_severity", "dme_positive", "patient_id", "eye_id"]).issubset(
        manifest.columns
    )

    row_left = manifest.loc[manifest["sample_id"] == "10_left"].iloc[0]
    assert row_left["dataset_source"] == "eyepacs"
    assert row_left["dr_severity"] == 2
    assert row_left["image_path"].startswith("train/")
    assert row_left["patient_id"] == "10"
    assert row_left["eye_id"] == "left"
