from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings

import pandas as pd

from conformal_pathways.ingest.base import DatasetBuilder, as_root_relative


class Messidor2Builder(DatasetBuilder):
    name = "messidor2"

    def _resolve(self, root: Path, path_like: str | Path) -> Path:
        path = Path(path_like)
        return path if path.is_absolute() else root / path

    def _resolve_row_image(self, images_dir: Path, id_code: str) -> Path | None:
        image_path = images_dir / id_code
        if image_path.exists():
            return image_path

        suffix = Path(id_code).suffix
        stem = id_code[: -len(suffix)] if suffix else id_code
        fallback_suffix: str | None = None
        if suffix == ".JPG":
            fallback_suffix = ".jpg"
        elif suffix == ".jpg":
            fallback_suffix = ".JPG"
        elif suffix == ".PNG":
            fallback_suffix = ".png"
        elif suffix == ".png":
            fallback_suffix = ".PNG"

        if fallback_suffix is None:
            return None

        fallback_path = images_dir / f"{stem}{fallback_suffix}"
        return fallback_path if fallback_path.exists() else None

    def build_manifest(
        self,
        root: Path,
        out_csv: Path,
        **kwargs: Any,
    ) -> Path | dict[str, Any]:
        dry_run = bool(kwargs.pop("dry_run", False))
        labels_csv = self._resolve(root, kwargs.pop("labels_csv", "messidor_data.csv"))
        images_dir = self._resolve(
            root,
            kwargs.pop("images_dir", "messidor-2/messidor-2/preprocess"),
        )

        labels_df = pd.read_csv(labels_csv)
        records: list[dict[str, Any]] = []
        skipped_missing = 0

        for _, row in labels_df.iterrows():
            id_code = str(row["id_code"]).strip()
            sample_id = Path(id_code).stem
            image_path = self._resolve_row_image(images_dir, id_code)
            if image_path is None:
                skipped_missing += 1
                continue

            records.append(
                {
                    "sample_id": sample_id,
                    "image_path": as_root_relative(root, image_path),
                    "dataset_source": self.name,
                    "dr_severity": int(row["diagnosis"]),
                    "dme_positive": int(row["adjudicated_dme"]) > 0,
                    "adjudicated_gradable": int(row["adjudicated_gradable"]),
                    "patient_id": sample_id,
                    "eye_id": None,
                }
            )

        if skipped_missing > 0:
            warnings.warn(
                f"{self.name}: skipped {skipped_missing} rows due to missing image files",
                stacklevel=2,
            )

        df = pd.DataFrame.from_records(
            records,
            columns=[
                "sample_id",
                "image_path",
                "dataset_source",
                "dr_severity",
                "dme_positive",
                "adjudicated_gradable",
                "patient_id",
                "eye_id",
            ],
        )
        stats = {
            "n_rows": len(df),
            "source_rows": len(labels_df),
            "skipped_missing": skipped_missing,
        }
        return self.finalize_manifest(df=df, out_csv=out_csv, dry_run=dry_run, stats=stats)
