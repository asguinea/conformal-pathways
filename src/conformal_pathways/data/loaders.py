from __future__ import annotations

from numbers import Real
from typing import Any

import pandas as pd

from .schema import Observation, Sample, validate_samples


def normalize_dr_severity(value: Any) -> int | str:
    if isinstance(value, bool):
        raise ValueError("invalid dr_severity")
    if isinstance(value, Real) and value in (0, 1, 2, 3, 4):
        return int(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"0", "1", "2", "3", "4"}:
            return int(token)
        if token in {"mild", "moderate", "severe"}:
            return token
    raise ValueError(f"invalid dr_severity: {value!r}")


def normalize_glaucoma_risk(value: Any) -> str:
    token = str(value).strip().lower()
    if token not in {"low", "high"}:
        raise ValueError(f"invalid glaucoma_risk: {value!r}")
    return token


def normalize_bool(value: Any) -> bool:
    # CSV values may be Python/numpy numerics or strings. Unknown is handled
    # separately by the loader; arbitrary truthiness is never used.
    token = str(value).strip().lower()
    if token in {"true", "1", "1.0"}:
        return True
    if token in {"false", "0", "0.0"}:
        return False
    raise ValueError(f"invalid Boolean label: {value!r}")


def _normalize_label(key: str, value: Any) -> Any:
    if key == "dr_severity":
        return normalize_dr_severity(value)
    if key == "glaucoma_risk":
        return normalize_glaucoma_risk(value)
    if key in {"dme_positive", "dme_label_available"}:
        return normalize_bool(value)
    return value


def load_samples_from_csv(
    csv_path: str,
    dataset_source: str | None,
    id_col: str = "sample_id",
    image_col: str = "image_path",
    label_cols: list[str] | None = None,
    meta_cols: list[str] | None = None,
    observation_cols: dict[str, str] | None = None,
) -> list[Sample]:
    # Read strings first: preserve leading zeros in IDs and reject ambiguous labels.
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    if id_col not in df:
        raise ValueError(f"missing ID column: {id_col}")
    label_cols = label_cols or []
    meta_cols = list(dict.fromkeys([*(meta_cols or []), "split_hint", "split_provenance"]))
    observation_cols = observation_cols or {}
    if set(observation_cols.values()) & (
        set(label_cols) | {"dr_severity", "dme_positive", "glaucoma_risk", "dme_label_available"}
    ):
        raise ValueError("observation columns must be separate from target columns")
    if set(observation_cols.values()) - set(df.columns):
        raise ValueError("missing declared observation column")
    samples = []
    missing = {"", "na", "nan", "null", "none"}

    def present(value):
        return str(value).strip().lower() not in missing

    for row in df.to_dict("records"):
        source = dataset_source or row.get("dataset_source", "")
        labels = {
            k: _normalize_label(k, row[k]) for k in label_cols if k in row and present(row[k])
        }
        if present(row.get("dme_label_available", "")):
            availability = normalize_bool(row["dme_label_available"])
            if availability != present(row.get("dme_positive", "")):
                raise ValueError("dme_label_available contradicts dme_positive presence")
        labels.pop("dme_label_available", None)
        meta = {k: row[k] for k in meta_cols if k in row and present(row[k])}
        observed = {
            key: Observation(_normalize_label(key, row[col]), source=f"column:{col}")
            for key, col in observation_cols.items()
            if present(row[col])
        }
        image = row.get(image_col)
        samples.append(
            Sample(
                row[id_col],
                source,
                image if image and present(image) else None,
                labels,
                meta,
                observed,
            )
        )
    validate_samples(samples)
    return samples


def filter_dme_labeled(samples: list[Sample]) -> list[Sample]:
    return [sample for sample in samples if sample.dme_label_available()]
