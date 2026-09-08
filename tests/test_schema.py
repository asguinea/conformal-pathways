import json

import pytest

from conformal_pathways.data import Sample


def test_grouping_priority_patient_eye_encounter_sample() -> None:
    sample = Sample(
        sample_id="s1",
        dataset_source="dataset_a",
        image_path=None,
        labels={},
        meta={
            "patient_id": "p1",
            "eye_id": "e1",
            "encounter_id": "enc1",
        },
    )
    assert sample.group_id() == json.dumps(["dataset_a", "patient_id", "p1"])

    sample.meta = {"eye_id": "e1", "encounter_id": "enc1"}
    assert sample.group_id() == json.dumps(["dataset_a", "eye_id", "e1"])

    sample.meta = {"encounter_id": "enc1"}
    assert sample.group_id() == json.dumps(["dataset_a", "encounter_id", "enc1"])

    sample.meta = {}
    assert sample.group_id() == json.dumps(["dataset_a", "sample_id", "s1"])


def test_dme_label_available() -> None:
    sample_true = Sample(
        sample_id="s1",
        dataset_source="dataset_a",
        image_path=None,
        labels={"dme_positive": True},
        meta={},
    )
    assert sample_true.dme_label_available() is True

    sample_missing = Sample(
        sample_id="s2",
        dataset_source="dataset_a",
        image_path=None,
        labels={},
        meta={},
    )
    assert sample_missing.dme_label_available() is False

    sample_non_bool = Sample(
        sample_id="s3",
        dataset_source="dataset_a",
        image_path=None,
        labels={"dme_positive": "yes"},
        meta={},
    )
    assert sample_non_bool.dme_label_available() is False


def test_validate_raises_on_missing_sample_id_or_dataset_source() -> None:
    missing_sample_id = Sample(
        sample_id="",
        dataset_source="dataset_a",
        image_path=None,
        labels={},
        meta={},
    )
    with pytest.raises(ValueError, match="sample_id must be a non-empty string"):
        missing_sample_id.validate()

    missing_dataset_source = Sample(
        sample_id="s1",
        dataset_source="",
        image_path=None,
        labels={},
        meta={},
    )
    with pytest.raises(ValueError, match="dataset_source must be a non-empty string"):
        missing_dataset_source.validate()
