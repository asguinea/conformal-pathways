from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


def parse_subgroup_keys(subgroup_keys: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if subgroup_keys is None:
        return []
    if isinstance(subgroup_keys, str):
        parts = [part.strip() for part in subgroup_keys.split(",")]
        return [part for part in parts if part]
    return [str(part).strip() for part in subgroup_keys if str(part).strip()]


def _sanitize_token(value: Any) -> str:
    token = re.sub(r"[^0-9A-Za-z]+", "_", str(value)).strip("_")
    return token or "na"


def make_run_tag(*parts: Any) -> str:
    return "__".join(_sanitize_token(part) for part in parts if part is not None)


def default_per_sample_csv_path(run_tag: str, out_dir: str = "artifacts/results") -> str:
    return str(Path(out_dir) / f"{make_run_tag(run_tag)}_per_sample.csv")


def _sample_lookup(sample: Any, key: str, default: Any = None) -> Any:
    if hasattr(sample, key):
        return getattr(sample, key)
    if isinstance(sample, dict):
        if key in sample:
            return sample[key]
        labels = sample.get("labels", {})
        meta = sample.get("meta", {})
    else:
        labels = getattr(sample, "labels", {})
        meta = getattr(sample, "meta", {})

    if isinstance(meta, dict) and key in meta:
        return meta[key]
    if isinstance(labels, dict) and key in labels:
        return labels[key]
    return default


def build_per_sample_rows(
    samples: list[Any],
    per_sample_metrics: list[dict[str, Any]],
    extra_fields: dict[str, Any] | None = None,
    subgroup_keys: str | list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    if len(samples) != len(per_sample_metrics):
        raise ValueError(
            "samples and per_sample_metrics length mismatch: "
            f"{len(samples)} != {len(per_sample_metrics)}"
        )

    subgroup_cols = parse_subgroup_keys(subgroup_keys)
    metric_cols: list[str] = []
    for metric_row in per_sample_metrics:
        for key in metric_row:
            if key not in metric_cols:
                metric_cols.append(key)

    extra_fields = extra_fields or {}
    extra_cols = list(extra_fields.keys())

    base_cols = ["sample_id", "dataset_source", "patient_id", "eye_id"]
    ordered_cols: list[str] = []
    for col in base_cols + subgroup_cols + metric_cols + extra_cols:
        if col not in ordered_cols:
            ordered_cols.append(col)

    rows: list[dict[str, Any]] = []
    for idx, sample in enumerate(samples):
        row: dict[str, Any] = {
            "sample_id": _sample_lookup(sample, "sample_id"),
            "dataset_source": _sample_lookup(sample, "dataset_source"),
            "patient_id": _sample_lookup(sample, "patient_id"),
            "eye_id": _sample_lookup(sample, "eye_id"),
        }

        for subgroup_col in subgroup_cols:
            row[subgroup_col] = _sample_lookup(sample, subgroup_col)

        metric_row = per_sample_metrics[idx]
        for metric_col in metric_cols:
            row[metric_col] = metric_row.get(metric_col)

        for extra_col, extra_value in extra_fields.items():
            if isinstance(extra_value, (list, tuple)):
                row[extra_col] = extra_value[idx] if idx < len(extra_value) else None
            else:
                row[extra_col] = extra_value

        rows.append(row)

    return pd.DataFrame(rows, columns=ordered_cols)


def write_per_sample_csv(df: pd.DataFrame, path: str) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return str(out_path)
