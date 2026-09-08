from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings

import pandas as pd

from conformal_pathways.ingest.base import DatasetBuilder, as_root_relative, resolve_image_file


class EyePACSBuilder(DatasetBuilder):
    name = "eyepacs"

    def build_manifest(
        self,
        root: Path,
        out_csv: Path,
        **kwargs: Any,
    ) -> Path | dict[str, Any]:
        dry_run = bool(kwargs.pop("dry_run", False))
        labels_csv = kwargs.pop("labels_csv", root / "trainLabels.csv")
        images_dir = kwargs.pop("images_dir", root / "train")

        labels_csv = Path(labels_csv)
        images_dir = Path(images_dir)
        if not labels_csv.is_absolute():
            labels_csv = root / labels_csv
        if not images_dir.is_absolute():
            images_dir = root / images_dir

        labels_df = pd.read_csv(labels_csv)
        records: list[dict[str, Any]] = []
        skipped_missing = 0

        for _, row in labels_df.iterrows():
            sample_id = str(row["image"]).strip()
            image_path = resolve_image_file(images_dir, sample_id)
            if image_path is None:
                skipped_missing += 1
                continue

            if "_" in sample_id:
                patient_id, eye_id = sample_id.split("_", 1)
            else:
                patient_id, eye_id = sample_id, None

            records.append(
                {
                    "sample_id": sample_id,
                    "image_path": as_root_relative(root, image_path),
                    "dataset_source": self.name,
                    "dr_severity": int(row["level"]),
                    "dme_positive": None,
                    "patient_id": patient_id,
                    "eye_id": eye_id,
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
