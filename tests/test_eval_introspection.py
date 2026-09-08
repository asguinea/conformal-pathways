from __future__ import annotations

from conformal_pathways.data import Sample
from conformal_pathways.eval.introspection import describe_prediction_set
from conformal_pathways.eval.runner import run_synthetic_experiment
from conformal_pathways.workflows import Action, DRWorkflow, Pathway


def test_describe_prediction_set_returns_non_empty_string() -> None:
    workflow = DRWorkflow()
    sample = Sample(
        sample_id="sample_0",
        dataset_source="synthetic",
        image_path=None,
        labels={"dr_severity": "moderate", "dme_positive": True, "dme_label_available": True},
        meta={"patient_id": "p0"},
    )
    pi = [
        Pathway(
            actions=[
                Action("order_OCT"),
                Action("refer_retina"),
                Action("followup", {"weeks": 4}),
            ]
        )
    ]

    description = describe_prediction_set(
        pi=pi,
        workflow=workflow,
        sample=sample,
        extra_context={"thresholds": {1: 0.5, 2: 0.5, 3: 0.5}},
    )

    assert isinstance(description, str)
    assert description.strip() != ""
    assert "prediction_set Pi(X0)" in description
    assert "safety_oracle" in description


def test_debug_eval_introspection_smoke(capsys) -> None:
    metrics = run_synthetic_experiment(
        workflow_name="dr_workflow",
        n=20,
        seed=0,
        alpha=0.1,
        debug_eval_introspection=True,
    )

    captured = capsys.readouterr()
    assert "Evaluation Introspection" in captured.out
    assert "existential_safe" in metrics
    assert "oracle_retained" in metrics


def test_selection_policy_print_smoke(capsys) -> None:
    _ = run_synthetic_experiment(
        workflow_name="dr_workflow",
        n=20,
        seed=0,
        alpha=0.1,
        selection_policies="observed_rules_first,min_rule_penalty",
        debug_print_selected_paths=True,
    )
    captured = capsys.readouterr()
    assert "[observed_rules_first] selected:" in captured.out
    assert "[min_rule_penalty] selected:" in captured.out
