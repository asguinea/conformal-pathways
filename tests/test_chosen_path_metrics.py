from __future__ import annotations

from conformal_pathways.data import Sample
from conformal_pathways.eval.metrics import aggregate_chosen_path_metrics, compute_chosen_path_metrics
from conformal_pathways.workflows import Action, DRWorkflow, Pathway


def _sample_dme_positive() -> Sample:
    return Sample(
        sample_id="s_pos",
        dataset_source="synthetic",
        image_path=None,
        labels={
            "dr_severity": "moderate",
            "dme_positive": True,
            "dme_label_available": True,
        },
        meta={"patient_id": "p0"},
    )


def _sample_dme_negative() -> Sample:
    return Sample(
        sample_id="s_neg",
        dataset_source="synthetic",
        image_path=None,
        labels={
            "dr_severity": "moderate",
            "dme_positive": False,
            "dme_label_available": True,
        },
        meta={"patient_id": "p1"},
    )


def test_compute_chosen_path_metrics_safe_and_unsafe_policies() -> None:
    workflow = DRWorkflow()
    sample = _sample_dme_negative()

    safe_path = Pathway(
        actions=[
            Action("order_OCT"),
            Action("monitor"),
            Action("followup", {"weeks": 12}),
        ]
    )
    unsafe_path = Pathway(
        actions=[
            Action("order_OCT"),
            Action("anti_VEGF"),
            Action("followup", {"weeks": 12}),
        ]
    )
    pi = [unsafe_path, safe_path]

    chosen = compute_chosen_path_metrics(
        prediction_set=pi,
        workflow=workflow,
        workflow_name=workflow.name,
        sample=sample,
        predictor=None,
        selection_policies=["guideline_first", "min_rule_penalty"],
    )

    # guideline_first should select monitor+12 for dme_negative (safe)
    assert chosen["chosen_is_safe__guideline_first"] is True
    assert chosen["chosen_is_unsafe__guideline_first"] is False
    assert chosen["chosen_is_empty__guideline_first"] is False

    # min_rule_penalty ties on penalty and falls back lexicographic -> anti_VEGF first (unsafe)
    assert chosen["chosen_is_safe__min_rule_penalty"] is False
    assert chosen["chosen_is_unsafe__min_rule_penalty"] is True
    assert chosen["chosen_is_empty__min_rule_penalty"] is False

    aggregated = aggregate_chosen_path_metrics([chosen])
    assert aggregated["chosen_safe_rate__guideline_first"] == 1.0
    assert aggregated["chosen_unsafe_rate__guideline_first"] == 0.0
    assert aggregated["chosen_unsafe_rate__min_rule_penalty"] == 1.0


def test_compute_chosen_path_metrics_empty_prediction_set_conservative() -> None:
    workflow = DRWorkflow()
    sample = _sample_dme_positive()

    chosen = compute_chosen_path_metrics(
        prediction_set=[],
        workflow=workflow,
        workflow_name=workflow.name,
        sample=sample,
        predictor=None,
        selection_policies=["guideline_first"],
    )
    assert chosen["chosen_is_empty__guideline_first"] is True
    assert chosen["chosen_is_safe__guideline_first"] is False
    assert chosen["chosen_is_unsafe__guideline_first"] is True

    aggregated = aggregate_chosen_path_metrics([chosen])
    assert aggregated["chosen_empty_rate__guideline_first"] == 1.0
    assert aggregated["chosen_unsafe_rate__guideline_first"] == 1.0
