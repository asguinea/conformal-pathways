from __future__ import annotations

import json

import pandas as pd

from conformal_pathways.data.loaders import filter_dme_labeled, load_samples_from_csv


def test_load_samples_from_csv_populates_labels_meta_and_grouping(tmp_path) -> None:
    csv_path = tmp_path / "manifest.csv"
    df = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "image_path": "/tmp/a.png",
                "dr_severity": "mild",
                "dme_positive": True,
                "patient_id": "p1",
            },
            {
                "sample_id": "s2",
                "image_path": "/tmp/b.png",
                "dr_severity": "moderate",
                "dme_positive": False,
                "patient_id": "p1",
            },
            {
                "sample_id": "s3",
                "image_path": "/tmp/c.png",
                "dr_severity": "severe",
                "dme_positive": True,
                "patient_id": "p2",
            },
        ]
    )
    df.to_csv(csv_path, index=False)

    samples = load_samples_from_csv(
        csv_path=str(csv_path),
        dataset_source="dataset_x",
        label_cols=["dr_severity", "dme_positive"],
        meta_cols=["patient_id"],
    )

    assert len(samples) == 3
    assert samples[0].sample_id == "s1"
    assert samples[0].labels["dr_severity"] == "mild"
    assert samples[0].labels["dme_positive"] is True
    assert samples[0].meta["patient_id"] == "p1"
    assert samples[0].group_id() == json.dumps(["dataset_x", "patient_id", "p1"])
    assert samples[2].group_id() == json.dumps(["dataset_x", "patient_id", "p2"])


def test_filter_dme_labeled_keeps_only_boolean_labels(tmp_path) -> None:
    csv_path = tmp_path / "manifest_bool_filter.csv"
    df = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "image_path": "/tmp/a.png",
                "dr_severity": "mild",
                "dme_positive": True,
                "patient_id": "p1",
            },
            {
                "sample_id": "s2",
                "image_path": "/tmp/b.png",
                "dr_severity": "moderate",
                "dme_positive": None,
                "patient_id": "p2",
            },
            {
                "sample_id": "s3",
                "image_path": "/tmp/c.png",
                "dr_severity": "severe",
                "dme_positive": False,
                "patient_id": "p3",
            },
        ]
    )
    df.to_csv(csv_path, index=False)

    samples = load_samples_from_csv(
        csv_path=str(csv_path),
        dataset_source="dataset_y",
        label_cols=["dr_severity", "dme_positive"],
        meta_cols=["patient_id"],
    )
    filtered = filter_dme_labeled(samples)

    assert [sample.sample_id for sample in filtered] == ["s1", "s3"]


def test_loader_rejects_contradictory_availability_even_without_flag_in_label_cols(tmp_path):
    import pytest

    path = tmp_path / "labels.csv"
    path.write_text("sample_id,dme_positive,dme_label_available\na,true,false\n")
    with pytest.raises(ValueError, match="contradicts"):
        load_samples_from_csv(str(path), "s", label_cols=["dme_positive"])


def test_observation_cannot_alias_a_known_target_column(tmp_path):
    import pytest

    path = tmp_path / "labels.csv"
    path.write_text("sample_id,dme_positive\na,true\n")
    with pytest.raises(ValueError, match="separate"):
        load_samples_from_csv(str(path), "s", observation_cols={"dme_positive": "dme_positive"})
