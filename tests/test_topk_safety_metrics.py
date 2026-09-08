from __future__ import annotations

from conformal_pathways.data import Sample
from conformal_pathways.eval.metrics import aggregate_topk_safety_metrics, compute_topk_safety_metrics
from conformal_pathways.eval.selection_policies import rank_pathways
from conformal_pathways.safety import is_safe
from conformal_pathways.workflows import Action, DRWorkflow, Pathway


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
        meta={"patient_id": "p0"},
    )


def test_topk_safety_first_unsafe_second_safe() -> None:
    workflow = DRWorkflow()
    sample = _sample_dme_negative()

    unsafe_first = Pathway(
        actions=[
            Action("order_OCT"),
            Action("anti_VEGF"),
            Action("followup", {"weeks": 12}),
        ]
    )
    safe_second = Pathway(
        actions=[
            Action("order_OCT"),
            Action("monitor"),
            Action("followup", {"weeks": 12}),
        ]
    )
    pi = [unsafe_first, safe_second]
    ranking_policy = "min_rule_penalty"

    ranked = rank_pathways(
        pi=pi,
        workflow=workflow,
        sample=sample,
        predictor=None,
        policy=ranking_policy,
    )
    sample_meta = {**sample.labels, **sample.meta}
    first_is_safe = is_safe(
        workflow.name,
        sample_meta,
        workflow.rollout(sample_meta, ranked[0]),
        ranked[0],
    )
    assert first_is_safe is False

    topk = compute_topk_safety_metrics(
        prediction_set=pi,
        workflow=workflow,
        workflow_name=workflow.name,
        sample=sample,
        predictor=None,
        ranking_policies=[ranking_policy],
        ks=(2, 3),
    )
    assert topk["top2_has_safe__min_rule_penalty"] is True
    assert topk["top3_has_safe__min_rule_penalty"] is True


def test_topk_safety_empty_prediction_set() -> None:
    workflow = DRWorkflow()
    sample = _sample_dme_negative()

    topk = compute_topk_safety_metrics(
        prediction_set=[],
        workflow=workflow,
        workflow_name=workflow.name,
        sample=sample,
        predictor=None,
        ranking_policies=["guideline_first"],
        ks=(2, 3),
    )
    assert topk["top2_has_safe__guideline_first"] is False
    assert topk["top3_has_safe__guideline_first"] is False

    aggregated = aggregate_topk_safety_metrics(
        per_sample_topk_metrics=[topk],
        ranking_policies=["guideline_first"],
        ks=(2, 3),
    )
    assert aggregated["top2_has_safe_rate__guideline_first"] == 0.0
    assert aggregated["top3_has_safe_rate__guideline_first"] == 0.0
