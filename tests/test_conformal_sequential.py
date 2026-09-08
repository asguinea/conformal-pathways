from __future__ import annotations

import pytest

from conformal_pathways.conformal.sequential import build_prediction_set
from conformal_pathways.data import Sample
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows.dr import DRWorkflow


def _dr_sample(
    sample_id: str,
    dr_severity: str,
    dme_positive: bool,
    dme_label_available: bool,
) -> Sample:
    return Sample(
        sample_id=sample_id,
        dataset_source="synthetic_dr",
        image_path=None,
        labels={
            "dr_severity": dr_severity,
            "dme_positive": dme_positive,
            "dme_label_available": dme_label_available,
        },
        meta={},
    )


def _path_signatures(paths) -> list[tuple[tuple[str, tuple[tuple[str, str], ...]], ...]]:
    return [
        tuple(
            (
                action.name,
                tuple((key, repr(value)) for key, value in sorted(action.params.items())),
            )
            for action in path.actions
        )
        for path in paths
    ]


def test_build_prediction_set_high_threshold_keeps_all_paths() -> None:
    workflow = DRWorkflow()
    sample = _dr_sample("s1", "moderate", True, True)
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit([sample])

    paths = build_prediction_set(
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        workflow_name=workflow.name,
        thresholds={1: 999.0, 2: 999.0, 3: 999.0},
    )

    assert len(paths) == 18


def test_build_prediction_set_low_threshold_prunes_no_oct() -> None:
    workflow = DRWorkflow()
    sample = _dr_sample("s2", "moderate", True, True)
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit([sample])

    paths = build_prediction_set(
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        workflow_name=workflow.name,
        thresholds={1: 0.0, 2: 0.0, 3: 0.0},
        w_u=0.0,
        w_r=1.0,
    )

    assert len(paths) < 18
    assert all("no_OCT" not in path.to_names() for path in paths)


def test_build_prediction_set_is_deterministic() -> None:
    workflow = DRWorkflow()
    sample = _dr_sample("s3", "mild", False, True)
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit([sample])

    paths_1 = build_prediction_set(
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        workflow_name=workflow.name,
        thresholds={1: 999.0, 2: 999.0, 3: 999.0},
    )
    paths_2 = build_prediction_set(
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        workflow_name=workflow.name,
        thresholds={1: 999.0, 2: 999.0, 3: 999.0},
    )

    assert _path_signatures(paths_1) == _path_signatures(paths_2)


def test_path_count_truncation_is_rejected():
    with pytest.raises(ValueError, match="invalidate"):
        build_prediction_set(
            DRWorkflow(),
            _dr_sample("s", "moderate", True, True),
            None,
            "dr_workflow",
            {1: float("inf"), 2: float("inf"), 3: float("inf")},
            max_paths=5,
        )
