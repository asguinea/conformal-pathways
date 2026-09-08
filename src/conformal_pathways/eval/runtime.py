from __future__ import annotations


def _percentile_from_sorted(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])

    rank = (len(values) - 1) * (percentile / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(values) - 1)
    weight = rank - lower
    return float(values[lower] * (1.0 - weight) + values[upper] * weight)


def summarize_runtime_ms(durations_ms: list[float]) -> dict[str, float]:
    if not durations_ms:
        return {
            "runtime_ms_mean_per_sample": 0.0,
            "runtime_ms_p50_per_sample": 0.0,
            "runtime_ms_p95_per_sample": 0.0,
            "runtime_ms_total": 0.0,
        }

    sorted_values = sorted(float(value) for value in durations_ms)
    total = float(sum(sorted_values))
    n = len(sorted_values)
    return {
        "runtime_ms_mean_per_sample": total / n,
        "runtime_ms_p50_per_sample": _percentile_from_sorted(sorted_values, 50.0),
        "runtime_ms_p95_per_sample": _percentile_from_sorted(sorted_values, 95.0),
        "runtime_ms_total": total,
    }
