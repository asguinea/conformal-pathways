from __future__ import annotations

import pandas as pd

from conformal_pathways.ingest.messidor2 import Messidor2Builder


def test_messidor2_builder_manifest(tmp_path) -> None:
    root = tmp_path
    images_dir = root / "messidor-2/messidor-2/preprocess"
    images_dir.mkdir(parents=True)

    (images_dir / "img_001.png").write_bytes(b"img")
    (images_dir / "IM000012.jpg").write_bytes(b"img")

    labels = pd.DataFrame(
        [
            {
                "id_code": "img_001.png",
                "diagnosis": 3,
                "adjudicated_dme": 1,
                "adjudicated_gradable": 1,
            },
            {
                "id_code": "IM000012.JPG",
                "diagnosis": 0,
                "adjudicated_dme": 0,
                "adjudicated_gradable": 1,
            },
        ]
    )
    labels.to_csv(root / "messidor_data.csv", index=False)

    builder = Messidor2Builder()
    result = builder.build_manifest(root=root, out_csv=root / "manifest.csv", dry_run=True)
    manifest = result["df"]

    assert len(manifest) == 2
    row_png = manifest.loc[manifest["sample_id"] == "img_001"].iloc[0]
    row_jpg = manifest.loc[manifest["sample_id"] == "IM000012"].iloc[0]
    assert row_png["dr_severity"] == 3
    assert bool(row_png["dme_positive"]) is True
    assert row_jpg["dr_severity"] == 0
    assert bool(row_jpg["dme_positive"]) is False
    assert row_jpg["image_path"].lower().endswith("im000012.jpg")
    assert row_png["dataset_source"] == "messidor2"
    assert "adjudicated_gradable" in manifest.columns


def test_messidor_rejects_fractional_labels(tmp_path):
    import pytest

    (tmp_path / "case.jpg").write_bytes(b"image")
    labels = tmp_path / "labels.csv"
    labels.write_text("id_code,diagnosis,adjudicated_dme,adjudicated_gradable\ncase.jpg,1.5,0,1\n")
    with pytest.raises(ValueError, match="invalid"):
        Messidor2Builder().build_manifest(
            tmp_path, tmp_path / "out.csv", images_dir=".", labels_csv=labels, dry_run=True
        )
