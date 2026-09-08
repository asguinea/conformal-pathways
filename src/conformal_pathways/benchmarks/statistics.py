"""Intervals at the independent repetition unit; repeated splits are descriptive."""

from __future__ import annotations

import math
from statistics import NormalDist


def summarize_values(values, confidence=0.95, bounds=(0.0, 1.0), binary=False, independent=True):
    if not 0 < confidence < 1 or bounds[0] >= bounds[1]:
        raise ValueError("invalid interval configuration")
    usable = [float(v) for v in values if v is not None]
    if any(not math.isfinite(v) or not bounds[0] <= v <= bounds[1] for v in usable):
        raise ValueError("metric outside declared bounds")
    n = len(usable)
    result = {
        "n_units": n,
        "n_unavailable": len(values) - n,
        "mean": sum(usable) / n if n else None,
        "observed_min": min(usable) if n else None,
        "observed_max": max(usable) if n else None,
        "interval_low": None,
        "interval_high": None,
        "interval_method": "unavailable",
        "confidence": confidence if independent else None,
    }
    if not n:
        return result
    if not independent:
        result["interval_method"] = "descriptive_seed_range_only"
        return result
    mean = result["mean"]
    if binary:
        if any(v not in (0.0, 1.0) for v in usable) or bounds != (0.0, 1.0):
            raise ValueError("Wilson intervals require Bernoulli repetition outcomes")
        z = NormalDist().inv_cdf((1 + confidence) / 2)
        center = (mean + z * z / (2 * n)) / (1 + z * z / n)
        half = z * math.sqrt(mean * (1 - mean) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        low, high = max(0.0, center - half), min(1.0, center + half)
        method = "wilson_approximate"
    else:
        half = (bounds[1] - bounds[0]) * math.sqrt(math.log(2 / (1 - confidence)) / (2 * n))
        low, high = max(bounds[0], mean - half), min(bounds[1], mean + half)
        method = "hoeffding_bounded_independent_repetitions"
    result.update(interval_low=low, interval_high=high, interval_method=method)
    return result


def paired_summary(left, right, confidence=0.95, bounds=(0.0, 1.0), independent=True):
    if set(left) != set(right):
        raise ValueError("paired comparisons require identical repetition IDs")
    differences = [
        left[k] - right[k] if left[k] is not None and right[k] is not None else None
        for k in sorted(left)
    ]
    width = bounds[1] - bounds[0]
    result = summarize_values(differences, confidence, (-width, width), independent=independent)
    result["estimand"] = "mean_paired_difference_on_jointly_evaluable_repetitions"
    return result
