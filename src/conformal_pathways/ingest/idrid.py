from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings

import pandas as pd

from conformal_pathways.ingest.base import DatasetBuilder, as_root_relative, resolve_image_file


class IDRiDBuilder(DatasetBuilder):
    name = "idrid"

    def _resolve(self, root: Path, path_like: str | Path) -> Path:
        path = Path(path_like)
        return path if path.is_absolute() else root / path

    def _load_labels(self, csv_path: Path) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df.columns = [str(column).strip() for column in df.columns]
        return df

    def build_manifest(
        self,
        root: Path,
        out_csv: Path,
        **kwargs: Any,
    ) -> Path | dict[str, Any]:
        dry_run = bool(kwargs.pop("dry_run", False))
        training_images_dir = self._resolve(
            root,
            kwargs.pop(
                "training_images_dir",
                "B. Disease Grading/1. Original Images/a. Training Set",
            ),
        )
        testing_images_dir = self._resolve(
            root,
            kwargs.pop(
                "testing_images_dir",
                "B. Disease Grading/1. Original Images/b. Testing Set",
            ),
        )
        training_labels_csv = self._resolve(
            root,
            kwargs.pop(
                "training_labels_csv",
                "B. Disease Grading/2. Groundtruths/a_IDRiD_Disease_Grading_Training_Labels.csv",
            ),
        )
        testing_labels_csv = kwargs.pop("testing_labels_csv", None)
        testing_labels_path = (
            self._resolve(root, testing_labels_csv) if testing_labels_csv is not None else None
        )

        label_frames = [self._load_labels(training_labels_csv)]
        if testing_labels_path is not None and testing_labels_path.exists():
            label_frames.append(self._load_labels(testing_labels_path))

        labels_df = pd.concat(label_frames, ignore_index=True)
        records: list[dict[str, Any]] = []
        skipped_missing = 0

        for _, row in labels_df.iterrows():
            sample_id = str(row["Image name"]).strip()
            image_path = resolve_image_file(training_images_dir, sample_id)
            if image_path is None:
                image_path = resolve_image_file(testing_images_dir, sample_id)
            if image_path is None:
                skipped_missing += 1
                continue

            records.append(
                {
                    "sample_id": sample_id,
                    "image_path": as_root_relative(root, image_path),
                    "dataset_source": self.name,
                    "dr_severity": int(row["Retinopathy grade"]),
                    "dme_positive": int(row["Risk of macular edema"]) > 0,
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
