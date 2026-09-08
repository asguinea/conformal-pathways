from __future__ import annotations

import math
from decimal import ROUND_CEILING, Decimal


def allocate_alpha(
    alpha: float,
    T: int,
    mode: str = "uniform",
    stage_score_variances: dict[int, float] | None = None,
) -> dict[int, float]:
    if isinstance(alpha, bool) or not math.isfinite(alpha) or not 0 <= alpha < 1:
        raise ValueError("alpha must satisfy 0 <= alpha < 1")
    if isinstance(T, bool) or not isinstance(T, int) or T < 1:
        raise ValueError("T must be a positive integer")
    if stage_score_variances is not None or mode == "variance_weighted":
        raise ValueError(
            "variance_weighted allocation is removed: budgets must be fixed independently of calibration"
        )
    if mode == "uniform":
        weights = None
    elif mode in {"front_loaded", "back_loaded"}:
        if T != 3:
            raise ValueError(f"{mode} requires T=3")
        weights = [0.6, 0.3, 0.1] if mode == "front_loaded" else [0.2, 0.3, 0.5]
    else:
        raise ValueError(f"Unsupported mode {mode!r}")
    total_alpha = Decimal(str(alpha))
    exact = (
        [total_alpha / T] * T
        if weights is None
        else [total_alpha * Decimal(str(w)) for w in weights]
    )
    budgets = {}
    for i, value in enumerate(exact, 1):
        rounded = float(value)
        budgets[i] = math.nextafter(rounded, 0.0) if Decimal(str(rounded)) > value else rounded
    # Compare the decimal values actually passed to the quantile routine. Binary
    # summation of three 0.1 values must not create a spurious budget reduction.
    while sum(Decimal(str(v)) for v in budgets.values()) > total_alpha:
        largest = max(budgets, key=budgets.get)
        budgets[largest] = math.nextafter(budgets[largest], 0.0)
    return budgets


def conformal_quantile(scores: list[float], alpha_t: float) -> float:
    if not scores:
        raise ValueError("scores must be non-empty")
    if isinstance(alpha_t, bool) or not math.isfinite(alpha_t) or not 0 <= alpha_t < 1:
        raise ValueError("alpha_t must satisfy 0 <= alpha_t < 1")
    if any(isinstance(s, bool) or not math.isfinite(s) for s in scores):
        raise ValueError("calibration scores must be finite numbers")
    # Decimal spelling avoids erroneous extra ranks at e.g. 5 * (1 - 0.8).
    rank = int(
        (Decimal(len(scores) + 1) * (1 - Decimal(str(alpha_t)))).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    return math.inf if rank > len(scores) else float(sorted(scores)[rank - 1])


def compute_stage_thresholds(
    scores_by_stage: dict[int, list[float]], alpha: float, mode: str = "uniform"
) -> dict[int, float]:
    T = len(scores_by_stage)
    if T < 1 or set(scores_by_stage) != set(range(1, T + 1)):
        raise ValueError("scores must contain consecutive stages starting at 1")
    if len({len(v) for v in scores_by_stage.values()}) != 1:
        raise ValueError("each stage must contain the same calibration units")
    budgets = allocate_alpha(alpha, T, mode)
    return {t: conformal_quantile(values, budgets[t]) for t, values in scores_by_stage.items()}
