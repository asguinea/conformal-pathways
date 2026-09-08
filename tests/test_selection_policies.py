from __future__ import annotations

from conformal_pathways.data import Sample
from conformal_pathways.eval.selection_policies import (
    iter_pathways,
    normalize_selection_policies,
    render_pathway,
    select_pathway,
)
from conformal_pathways.workflows import Action, DRWorkflow, Pathway


def _dr_sample() -> Sample:
    return Sample(
        sample_id="dr_case_0",
        dataset_source="synthetic",
        image_path=None,
        labels={
            "dr_severity": "moderate",
            "dme_positive": True,
            "dme_label_available": True,
        },
        meta={"patient_id": "p0"},
    )


def test_iter_pathways_returns_expected_count() -> None:
    pi = [
        Pathway(
            actions=[Action("order_OCT"), Action("refer_retina"), Action("followup", {"weeks": 4})]
        ),
        Pathway(
            actions=[Action("order_OCT"), Action("monitor"), Action("followup", {"weeks": 12})]
        ),
    ]
    assert len(list(iter_pathways(pi))) == 2

    pi_dict = {"p1": pi[0], "p2": pi[1]}
    assert len(list(iter_pathways(pi_dict))) == 2


def test_select_pathway_returns_retained_member_and_is_deterministic() -> None:
    workflow = DRWorkflow()
    sample = _dr_sample()
    pi = [
        Pathway(
            actions=[Action("order_OCT"), Action("refer_retina"), Action("followup", {"weeks": 4})]
        ),
        Pathway(
            actions=[Action("order_OCT"), Action("monitor"), Action("followup", {"weeks": 12})]
        ),
    ]

    selected_1 = select_pathway(
        pi=pi, workflow=workflow, sample=sample, policy="observed_rules_first"
    )
    selected_2 = select_pathway(
        pi=pi, workflow=workflow, sample=sample, policy="observed_rules_first"
    )

    assert selected_1 in pi
    assert selected_2 in pi
    assert render_pathway(selected_1) == render_pathway(selected_2)


def test_min_rule_penalty_prefers_lower_rule_violations() -> None:
    workflow = DRWorkflow()
    sample = _dr_sample()

    low_penalty = Pathway(
        actions=[
            Action("order_OCT"),
            Action("refer_retina"),
            Action("followup", {"weeks": 4}),
        ]
    )
    high_penalty = Pathway(
        actions=[
            Action("no_OCT"),
            Action("monitor"),
            Action("followup", {"weeks": 24}),
        ]
    )
    pi = [high_penalty, low_penalty]

    selected = select_pathway(
        pi=pi,
        workflow=workflow,
        sample=sample,
        predictor=None,
        policy="min_rule_penalty",
    )
    assert selected == low_penalty


def test_normalize_selection_policies_parsing() -> None:
    assert normalize_selection_policies("") == []
    assert normalize_selection_policies("observed_rules_first,min_rule_penalty") == [
        "observed_rules_first",
        "min_rule_penalty",
    ]
