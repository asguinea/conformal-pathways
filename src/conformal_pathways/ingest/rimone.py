from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from conformal_pathways.ingest.base import DatasetBuilder, as_root_relative, list_image_files


class RIMONEBuilder(DatasetBuilder):
    name = "rimone"

    def _resolve(self, root: Path, path_like: str | Path) -> Path:
        path = Path(path_like)
        return path if path.is_absolute() else root / path

    def build_manifest(
        self,
        root: Path,
        out_csv: Path,
        **kwargs: Any,
    ) -> Path | dict[str, Any]:
        dry_run = bool(kwargs.pop("dry_run", False))
        base_dir = self._resolve(root, kwargs.pop("base_dir", "partitioned_randomly"))

        split_dirs = {
            "train": base_dir / "training_set",
            "test": base_dir / "test_set",
        }
        class_to_risk = {"glaucoma": "high", "normal": "low"}

        records: list[dict[str, Any]] = []
        for split_hint, split_dir in split_dirs.items():
            for class_name, risk in class_to_risk.items():
                class_dir = split_dir / class_name
                for image_path in list_image_files(class_dir):
                    sample_id = image_path.stem
                    records.append(
                        {
                            "sample_id": sample_id,
                            "image_path": as_root_relative(root, image_path),
                            "dataset_source": self.name,
                            "glaucoma_risk": risk,
                            "patient_id": None,
                            "eye_id": None,
                            "split_hint": split_hint,
                            "split_provenance": "provider_partitioned_randomly",
                        }
                    )

        df = pd.DataFrame.from_records(
            records,
            columns=[
                "sample_id",
                "image_path",
                "dataset_source",
                "glaucoma_risk",
                "patient_id",
                "eye_id",
                "split_hint",
                "split_provenance",
            ],
        )
        stats = {"n_rows": len(df), "source_rows": len(df), "skipped_missing": 0}
        return self.finalize_manifest(df=df, out_csv=out_csv, dry_run=dry_run, stats=stats)
