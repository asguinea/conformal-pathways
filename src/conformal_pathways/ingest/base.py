from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")


def list_image_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    files = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(files)


def resolve_image_file(directory: Path, stem_or_name: str) -> Path | None:
    candidate = directory / stem_or_name
    if candidate.exists() and candidate.is_file():
        return candidate

    stem = Path(stem_or_name).stem
    for ext in IMAGE_EXTENSIONS:
        candidate = directory / f"{stem}{ext}"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def as_root_relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path '{path}' is not under root '{root}'") from exc


def validate_manifest_df(df: pd.DataFrame) -> None:
    required = {"sample_id", "image_path", "dataset_source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"manifest missing required columns: {sorted(missing)}")

    if df["sample_id"].isna().any():
        raise ValueError("sample_id must not contain null values")
    if df["sample_id"].duplicated().any():
        duplicates = sorted(df.loc[df["sample_id"].duplicated(), "sample_id"].unique())
        raise ValueError(f"sample_id values must be unique, duplicates: {duplicates}")

    absolute_paths = [str(path) for path in df["image_path"] if Path(str(path)).is_absolute()]
    if absolute_paths:
        raise ValueError(
            "image_path must be root-relative; found absolute paths: "
            f"{absolute_paths[:3]}"
        )


class DatasetBuilder(ABC):
    name: str

    @abstractmethod
    def build_manifest(
        self,
        root: Path,
        out_csv: Path,
        **kwargs: Any,
    ) -> Path | dict[str, Any]:
        raise NotImplementedError

    def finalize_manifest(
        self,
        df: pd.DataFrame,
        out_csv: Path,
        dry_run: bool = False,
        stats: dict[str, Any] | None = None,
    ) -> Path | dict[str, Any]:
        validate_manifest_df(df)
        if dry_run:
            return {"df": df.copy(), "stats": stats or {}}

        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv, index=False)
        return out_csv
