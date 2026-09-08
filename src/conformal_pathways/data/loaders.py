from __future__ import annotations

from typing import Any

import pandas as pd

from conformal_pathways.data.schema import Sample


def normalize_dr_severity(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1, 2, 3, 4}:
        return value
    if isinstance(value, str) and value.lower() in {"mild", "moderate", "severe"}:
        return value.lower()
    return value


def normalize_glaucoma_risk(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"low", "high"}:
            return lowered
    return value


def _normalize_label(label_key: str, value: Any) -> Any:
    if label_key == "dr_severity":
        return normalize_dr_severity(value)
    if label_key == "glaucoma_risk":
        return normalize_glaucoma_risk(value)
    if label_key == "dme_positive":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
    return value


def load_samples_from_csv(
    csv_path: str,
    dataset_source: str,
    id_col: str = "sample_id",
    image_col: str = "image_path",
    label_cols: list[str] | None = None,
    meta_cols: list[str] | None = None,
) -> list[Sample]:
    df = pd.read_csv(csv_path)
    label_cols = label_cols or []
    meta_cols = meta_cols or []

    available_columns = set(df.columns)
    samples: list[Sample] = []

    for _, row in df.iterrows():
        sample_id = str(row[id_col])
        image_value = row[image_col] if image_col in available_columns else None
        image_path = None if pd.isna(image_value) else str(image_value)

        labels: dict[str, Any] = {}
        for label_col in label_cols:
            if label_col not in available_columns:
                continue
            value = row[label_col]
            if pd.isna(value):
                continue
            labels[label_col] = _normalize_label(label_col, value)

        meta: dict[str, Any] = {}
        for meta_col in meta_cols:
            if meta_col not in available_columns:
                continue
            value = row[meta_col]
            if pd.isna(value):
                continue
            meta[meta_col] = value

        sample = Sample(
            sample_id=sample_id,
            dataset_source=dataset_source,
            image_path=image_path,
            labels=labels,
            meta=meta,
        )
        sample.validate()
        samples.append(sample)

    return samples


def filter_dme_labeled(samples: list[Sample]) -> list[Sample]:
    return [sample for sample in samples if sample.dme_label_available()]
