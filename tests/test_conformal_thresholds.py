from __future__ import annotations

from conformal_pathways.conformal.thresholds import (
    allocate_alpha,
    compute_stage_thresholds,
    conformal_quantile,
)


def test_conformal_quantile_matches_known_values() -> None:
    scores = [0.1, 0.2, 0.3, 0.4, 0.5]

    assert conformal_quantile(scores, alpha_t=0.2) == 0.5
    assert conformal_quantile(scores, alpha_t=0.5) == 0.3
    assert conformal_quantile(scores, alpha_t=0.8) == 0.2


def test_allocate_alpha_uniform_sums() -> None:
    alpha_by_stage = allocate_alpha(alpha=0.3, T=3, mode="uniform")

    assert set(alpha_by_stage) == {1, 2, 3}
    assert abs(alpha_by_stage[1] - 0.1) < 1e-12
    assert abs(alpha_by_stage[2] - 0.1) < 1e-12
    assert abs(alpha_by_stage[3] - 0.1) < 1e-12
    assert abs(sum(alpha_by_stage.values()) - 0.3) < 1e-12


def test_allocate_alpha_variance_weighted_sums() -> None:
    alpha_by_stage = allocate_alpha(
        alpha=0.3,
        T=3,
        mode="variance_weighted",
        stage_score_variances={1: 1.0, 2: 2.0, 3: 3.0},
    )

    assert set(alpha_by_stage) == {1, 2, 3}
    assert abs(sum(alpha_by_stage.values()) - 0.3) < 1e-12
    assert alpha_by_stage[3] > alpha_by_stage[2] > alpha_by_stage[1]


def test_allocate_alpha_front_back_loaded_t3() -> None:
    alpha = 0.2
    front = allocate_alpha(alpha=alpha, T=3, mode="front_loaded")
    back = allocate_alpha(alpha=alpha, T=3, mode="back_loaded")

    assert abs(front[1] - 0.12) < 1e-12
    assert abs(front[2] - 0.06) < 1e-12
    assert abs(front[3] - 0.02) < 1e-12
    assert abs(back[1] - 0.04) < 1e-12
    assert abs(back[2] - 0.06) < 1e-12
    assert abs(back[3] - 0.10) < 1e-12
    assert abs(sum(front.values()) - alpha) < 1e-12
    assert abs(sum(back.values()) - alpha) < 1e-12


def test_allocate_alpha_front_back_loaded_requires_t3() -> None:
    try:
        allocate_alpha(alpha=0.2, T=4, mode="front_loaded")
    except ValueError as exc:
        assert "T=3" in str(exc)
    else:  # pragma: no cover - safety
        raise AssertionError("front_loaded should fail for T!=3")

    try:
        allocate_alpha(alpha=0.2, T=4, mode="back_loaded")
    except ValueError as exc:
        assert "T=3" in str(exc)
    else:  # pragma: no cover - safety
        raise AssertionError("back_loaded should fail for T!=3")


def test_compute_stage_thresholds_shapes() -> None:
    scores_by_stage = {
        1: [0.1] * 20,
        2: [i / 20.0 for i in range(1, 21)],
        3: [0.2 + (0.1 if i % 2 == 0 else 0.0) for i in range(20)],
    }

    thresholds_uniform = compute_stage_thresholds(
        scores_by_stage=scores_by_stage,
        alpha=0.3,
        mode="uniform",
    )
    thresholds_var = compute_stage_thresholds(
        scores_by_stage=scores_by_stage,
        alpha=0.3,
        mode="variance_weighted",
    )

    assert set(thresholds_uniform) == {1, 2, 3}
    assert set(thresholds_var) == {1, 2, 3}
    assert thresholds_var != thresholds_uniform
