from __future__ import annotations

from conformal_pathways.eval.runner import run_synthetic_experiment

REQUIRED_KEYS = {
    "existential_safe",
    "oracle_retained",
    "set_size",
    "empty_set_rate",
    "unsafe_exposure",
}


def _assert_metric_bounds(metrics: dict[str, object]) -> None:
    assert REQUIRED_KEYS.issubset(metrics.keys())
    assert "alpha_allocation" in metrics
    assert 0.0 <= metrics["existential_safe"] <= 1.0
    assert 0.0 <= metrics["oracle_retained"] <= 1.0
    assert 0.0 <= metrics["empty_set_rate"] <= 1.0
    assert 0.0 <= metrics["unsafe_exposure"] <= 1.0
    assert 0.0 < metrics["set_size"] <= 18.0


def test_run_synthetic_experiment_dr_smoke() -> None:
    metrics = run_synthetic_experiment(
        workflow_name="dr_workflow",
        n=20,
        seed=123,
        alpha=0.1,
    )

    _assert_metric_bounds(metrics)
    assert not any(key.startswith("chosen_") for key in metrics)
    assert not any(key.startswith("top2_has_safe_rate__") for key in metrics)
    assert not any(key.startswith("top3_has_safe_rate__") for key in metrics)
    assert not any(key.startswith("runtime_") for key in metrics)


def test_run_synthetic_experiment_glaucoma_smoke() -> None:
    metrics = run_synthetic_experiment(
        workflow_name="glaucoma_workflow",
        n=20,
        seed=123,
        alpha=0.1,
    )

    _assert_metric_bounds(metrics)


def test_run_synthetic_experiment_with_selection_policies_adds_chosen_columns() -> None:
    metrics = run_synthetic_experiment(
        workflow_name="dr_workflow",
        n=20,
        seed=123,
        alpha=0.1,
        selection_policies="observed_rules_first,min_rule_penalty",
    )

    _assert_metric_bounds(metrics)
    assert "chosen_unsafe_rate__observed_rules_first" in metrics
    assert "chosen_safe_rate__observed_rules_first" in metrics
    assert "chosen_empty_rate__observed_rules_first" in metrics
    assert "chosen_unsafe_rate__min_rule_penalty" in metrics
    assert "top2_has_safe_rate__observed_rules_first" in metrics
    assert "top3_has_safe_rate__observed_rules_first" in metrics


def test_run_synthetic_experiment_profile_runtime_adds_runtime_columns() -> None:
    metrics = run_synthetic_experiment(
        workflow_name="dr_workflow",
        n=20,
        seed=123,
        alpha=0.1,
        profile_runtime=True,
    )

    _assert_metric_bounds(metrics)
    assert "runtime_ms_mean_per_sample" in metrics
    assert "runtime_ms_p50_per_sample" in metrics
    assert "runtime_ms_p95_per_sample" in metrics
    assert "runtime_ms_total" in metrics
    assert float(metrics["runtime_ms_mean_per_sample"]) >= 0.0
    assert float(metrics["runtime_ms_p50_per_sample"]) >= 0.0
    assert float(metrics["runtime_ms_p95_per_sample"]) >= 0.0
    assert float(metrics["runtime_ms_total"]) >= 0.0
