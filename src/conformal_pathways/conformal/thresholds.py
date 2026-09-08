from __future__ import annotations

import math
import statistics


def allocate_alpha(
    alpha: float,
    T: int,
    mode: str,
    stage_score_variances: dict[int, float] | None = None,
) -> dict[int, float]:
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must satisfy 0 < alpha < 1")
    if T < 1:
        raise ValueError("T must be >= 1")

    if mode == "uniform":
        alpha_by_stage = {stage: alpha / T for stage in range(1, T + 1)}
    elif mode == "front_loaded":
        if T != 3:
            raise ValueError(
                "front_loaded alpha allocation currently supports only T=3"
            )
        alpha_by_stage = {
            1: 0.6 * alpha,
            2: 0.3 * alpha,
            3: 0.1 * alpha,
        }
    elif mode == "back_loaded":
        if T != 3:
            raise ValueError(
                "back_loaded alpha allocation currently supports only T=3"
            )
        alpha_by_stage = {
            1: 0.2 * alpha,
            2: 0.3 * alpha,
            3: 0.5 * alpha,
        }
    elif mode == "variance_weighted":
        if stage_score_variances is None:
            raise ValueError("stage_score_variances is required for variance_weighted mode")
        expected_keys = set(range(1, T + 1))
        if set(stage_score_variances) != expected_keys:
            raise ValueError(
                f"stage_score_variances keys must be {expected_keys}, got {set(stage_score_variances)}"
            )
        eps = 1e-12
        weights = {
            stage: float(stage_score_variances[stage]) + eps for stage in range(1, T + 1)
        }
        total_weight = sum(weights.values())
        alpha_by_stage = {
            stage: alpha * weights[stage] / total_weight for stage in range(1, T + 1)
        }
    else:
        raise ValueError(f"Unsupported mode '{mode}'")

    if not math.isclose(sum(alpha_by_stage.values()), alpha, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("allocated alpha does not sum to alpha")

    return alpha_by_stage


def conformal_quantile(scores: list[float], alpha_t: float) -> float:
    if not scores:
        raise ValueError("scores must be non-empty")
    if not (0.0 < alpha_t < 1.0):
        raise ValueError("alpha_t must satisfy 0 < alpha_t < 1")
    if any(math.isnan(score) for score in scores):
        raise ValueError("scores must not contain NaN")

    scores_sorted = sorted(scores)
    n = len(scores_sorted)
    k = math.ceil((n + 1) * (1.0 - alpha_t))
    k = min(max(k, 1), n)
    return scores_sorted[k - 1]


def compute_stage_thresholds(
    scores_by_stage: dict[int, list[float]],
    alpha: float,
    mode: str = "uniform",
) -> dict[int, float]:
    T = len(scores_by_stage)
    if T < 1:
        raise ValueError("scores_by_stage must contain at least one stage")

    expected_keys = set(range(1, T + 1))
    if set(scores_by_stage) != expected_keys:
        raise ValueError(
            f"scores_by_stage keys must be {expected_keys}, got {set(scores_by_stage)}"
        )

    stage_score_variances: dict[int, float] | None = None
    if mode == "variance_weighted":
        stage_score_variances = {}
        for stage in range(1, T + 1):
            stage_scores = scores_by_stage[stage]
            if any(math.isnan(score) for score in stage_scores):
                raise ValueError(f"scores for stage {stage} contain NaN")
            stage_score_variances[stage] = (
                statistics.pvariance(stage_scores) if len(stage_scores) > 1 else 0.0
            )

    alpha_by_stage = allocate_alpha(
        alpha=alpha,
        T=T,
        mode=mode,
        stage_score_variances=stage_score_variances,
    )

    return {
        stage: conformal_quantile(scores_by_stage[stage], alpha_by_stage[stage])
        for stage in range(1, T + 1)
    }
