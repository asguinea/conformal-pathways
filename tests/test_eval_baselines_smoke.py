from __future__ import annotations

import math

from conformal_pathways.eval.baselines import run_synthetic_comparison

EXPECTED_VARIANTS = {"main", "rules_only", "model_only", "no_conformal"}
EXPECTED_METRICS = {
    "existential_safe",
    "oracle_retained",
    "set_size",
    "empty_set_rate",
    "unsafe_exposure",
}


def _assert_metrics_shape_and_bounds(metrics: dict[str, float]) -> None:
    assert EXPECTED_METRICS.issubset(metrics.keys())
    for key in EXPECTED_METRICS:
        assert not math.isnan(metrics[key])

    assert 0.0 <= metrics["existential_safe"] <= 1.0
    assert 0.0 <= metrics["oracle_retained"] <= 1.0
    assert 0.0 <= metrics["empty_set_rate"] <= 1.0
    assert 0.0 <= metrics["unsafe_exposure"] <= 1.0
    assert 0.0 <= metrics["set_size"] <= 18.0


def test_run_synthetic_comparison_dr_smoke() -> None:
    comparison = run_synthetic_comparison(
        workflow_name="dr_workflow",
        n=30,
        seed=11,
        alpha=0.1,
    )

    assert EXPECTED_VARIANTS.issubset(comparison.keys())
    for variant in EXPECTED_VARIANTS:
        _assert_metrics_shape_and_bounds(comparison[variant])

    assert 0.0 <= comparison["rules_only"]["oracle_retained"] <= 1.0
    assert 0.0 <= comparison["model_only"]["oracle_retained"] <= 1.0


def test_run_synthetic_comparison_glaucoma_smoke() -> None:
    comparison = run_synthetic_comparison(
        workflow_name="glaucoma_workflow",
        n=30,
        seed=11,
        alpha=0.1,
    )

    assert EXPECTED_VARIANTS.issubset(comparison.keys())
    for variant in EXPECTED_VARIANTS:
        _assert_metrics_shape_and_bounds(comparison[variant])

    assert 0.0 <= comparison["rules_only"]["oracle_retained"] <= 1.0
    assert 0.0 <= comparison["model_only"]["oracle_retained"] <= 1.0
