from __future__ import annotations

from conformal_pathways.conformal import build_prediction_set
from conformal_pathways.data import Sample
from conformal_pathways.eval import compute_sample_metrics
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows.dr import DRWorkflow


def _dr_sample(sample_id: str, dme_positive: bool) -> Sample:
    return Sample(
        sample_id=sample_id,
        dataset_source="synthetic_dr",
        image_path=None,
        labels={
            "dr_severity": "moderate",
            "dme_positive": dme_positive,
            "dme_label_available": True,
        },
        meta={},
    )


def test_compute_sample_metrics_high_thresholds_include_all_paths() -> None:
    workflow = DRWorkflow()
    sample = _dr_sample("s1", dme_positive=True)
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit([sample, _dr_sample("s2", dme_positive=False)])

    prediction_set = build_prediction_set(
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        workflow_name=workflow.name,
        thresholds={1: 999.0, 2: 999.0, 3: 999.0},
    )
    metrics = compute_sample_metrics(
        workflow=workflow,
        workflow_name=workflow.name,
        sample=sample,
        prediction_set=prediction_set,
    )

    assert metrics["existential_safe"] is True
    assert metrics["oracle_retained"] is True
    assert metrics["set_size"] == 18
    assert 0.0 <= float(metrics["unsafe_exposure"]) <= 1.0


def test_compute_sample_metrics_low_threshold_prunes_no_oct_and_keeps_oracle() -> None:
    workflow = DRWorkflow()
    sample = _dr_sample("s3", dme_positive=True)
    predictor = TrivialLabelPredictor(
        label_key="dr_severity",
        class_values=["mild", "moderate", "severe"],
    )
    predictor.fit([sample, _dr_sample("s4", dme_positive=False)])

    prediction_set = build_prediction_set(
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        workflow_name=workflow.name,
        thresholds={1: 0.0, 2: 999.0, 3: 999.0},
        w_u=0.0,
        w_r=1.0,
    )
    metrics = compute_sample_metrics(
        workflow=workflow,
        workflow_name=workflow.name,
        sample=sample,
        prediction_set=prediction_set,
    )

    assert len(prediction_set) > 0
    assert all("no_OCT" not in pathway.to_names() for pathway in prediction_set)
    assert metrics["oracle_retained"] is True
    assert 0.0 <= float(metrics["unsafe_exposure"]) <= 1.0
