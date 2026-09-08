from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from conformal_pathways.ingest.base import DatasetBuilder, as_root_relative, list_image_files


class REFUGEBuilder(DatasetBuilder):
    name = "refuge"

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
        glaucoma_dir = self._resolve(root, kwargs.pop("glaucoma_dir", "Training400/Glaucoma"))
        non_dir = self._resolve(root, kwargs.pop("non_dir", "Training400/Non-Glaucoma"))

        records: list[dict[str, Any]] = []
        for image_path, risk in (
            *((path, "high") for path in list_image_files(glaucoma_dir)),
            *((path, "low") for path in list_image_files(non_dir)),
        ):
            sample_id = image_path.stem
            records.append(
                {
                    "sample_id": sample_id,
                    "image_path": as_root_relative(root, image_path),
                    "dataset_source": self.name,
                    "glaucoma_risk": risk,
                    "patient_id": sample_id,
                    "eye_id": None,
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
            ],
        )
        stats = {"n_rows": len(df), "source_rows": len(df), "skipped_missing": 0}
        return self.finalize_manifest(df=df, out_csv=out_csv, dry_run=dry_run, stats=stats)
