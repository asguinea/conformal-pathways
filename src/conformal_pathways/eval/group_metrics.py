from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd


def _sanitize_token(value: str) -> str:
    token = re.sub(r"[^0-9A-Za-z]+", "_", str(value)).strip("_")
    return token or "group"


def _metric_mappings(df: pd.DataFrame, metric_specs: Any = None) -> list[tuple[str, str]]:
    del metric_specs
    mappings: list[tuple[str, str]] = []

    base_mappings = [
        ("existential_safe", "existential_safe_rate"),
        ("unsafe_exposure", "unsafe_exposure_mean"),
        ("set_size", "set_size_mean"),
        ("empty_set", "empty_set_rate"),
    ]
    for source_col, target_col in base_mappings:
        if source_col in df.columns:
            mappings.append((source_col, target_col))

    for col in sorted(df.columns):
        if col.startswith("chosen_is_safe__"):
            mappings.append((col, col.replace("chosen_is_safe__", "chosen_safe_rate__")))
        elif col.startswith("chosen_is_unsafe__"):
            mappings.append((col, col.replace("chosen_is_unsafe__", "chosen_unsafe_rate__")))
        elif re.match(r"^top\d+_has_safe__", col):
            mappings.append((col, col.replace("_has_safe__", "_has_safe_rate__")))

    return mappings


def _is_safety_metric(metric_name: str) -> bool:
    return (
        metric_name == "existential_safe_rate"
        or metric_name.startswith("chosen_safe_rate__")
        or metric_name.startswith("top2_has_safe_rate__")
        or metric_name.startswith("top3_has_safe_rate__")
    )


def _is_risk_metric(metric_name: str) -> bool:
    return (
        metric_name == "unsafe_exposure_mean"
        or metric_name == "empty_set_rate"
        or metric_name.startswith("chosen_unsafe_rate__")
    )


def compute_group_metrics(
    per_sample_csv_path: str,
    group_key: str,
    metric_specs: Any = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(per_sample_csv_path)
    if group_key not in df.columns:
        raise ValueError(
            f"group_key '{group_key}' not found in per-sample CSV columns: {list(df.columns)}"
        )

    mappings = _metric_mappings(df, metric_specs=metric_specs)
    grouped = df.groupby(group_key, dropna=False)

    records: list[dict[str, Any]] = []
    for group_value, group_df in grouped:
        row: dict[str, Any] = {group_key: group_value, "n": int(len(group_df))}
        for source_col, target_col in mappings:
            row[target_col] = float(group_df[source_col].mean())
        records.append(row)

    if records:
        group_df = pd.DataFrame(records)
        group_df = group_df.sort_values(by=[group_key], key=lambda s: s.astype(str)).reset_index(
            drop=True
        )
    else:
        group_df = pd.DataFrame(columns=[group_key, "n"])

    worst_row: dict[str, Any] = {"group_key": group_key}
    metric_cols = [
        col
        for col in group_df.columns
        if col not in {group_key, "n"} and (_is_safety_metric(col) or _is_risk_metric(col))
    ]
    for metric_col in metric_cols:
        if _is_safety_metric(metric_col):
            idx = group_df[metric_col].idxmin()
        else:
            idx = group_df[metric_col].idxmax()
        metric_worst_row = group_df.loc[idx]
        worst_row[f"worst_group__{metric_col}"] = metric_worst_row[group_key]
        worst_row[f"worst_n__{metric_col}"] = int(metric_worst_row["n"])
        worst_row[f"worst_value__{metric_col}"] = float(metric_worst_row[metric_col])

    worst_df = pd.DataFrame([worst_row])
    return group_df, worst_df


def write_group_metric_outputs(
    per_sample_csv_path: str,
    group_key: str,
    out_dir: str,
    metric_specs: Any = None,
) -> tuple[str, str]:
    group_df, worst_df = compute_group_metrics(
        per_sample_csv_path=per_sample_csv_path,
        group_key=group_key,
        metric_specs=metric_specs,
    )

    out_base = Path(out_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    base_name = Path(per_sample_csv_path).stem
    group_token = _sanitize_token(group_key)

    group_path = out_base / f"{base_name}__groupby__{group_token}.csv"
    worst_path = out_base / f"{base_name}__worstgroup__{group_token}.csv"
    group_df.to_csv(group_path, index=False)
    worst_df.to_csv(worst_path, index=False)
    return str(group_path), str(worst_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute worst-group metrics from per-sample CSV.")
    parser.add_argument("--per_sample_csv", required=True)
    parser.add_argument("--group_key", required=True)
    parser.add_argument("--out_dir", default="artifacts/results")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    group_path, worst_path = write_group_metric_outputs(
        per_sample_csv_path=args.per_sample_csv,
        group_key=args.group_key,
        out_dir=args.out_dir,
    )
    print(f"group_metrics: {group_path}")
    print(f"worst_group: {worst_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
