from __future__ import annotations

import os
from typing import Any, Callable

import pandas as pd

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover - exercised only when PIL is missing
    Image = None  # type: ignore[assignment]

try:
    from torch.utils.data import Dataset
except ModuleNotFoundError:  # pragma: no cover - exercised only when torch is missing

    class Dataset:  # type: ignore[no-redef]
        pass


def resolve_image_path(dataset_root: str, image_path: str) -> str:
    if os.path.isabs(image_path):
        return image_path
    return os.path.join(dataset_root, image_path)


def _default_transform() -> Callable[[Any], Any]:
    try:
        from torchvision.models import ResNet50_Weights
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
        raise ImportError("torchvision is required for default image transforms") from exc

    return ResNet50_Weights.IMAGENET1K_V2.transforms()


class ManifestImageDataset(Dataset):
    def __init__(
        self,
        manifest_csv: str,
        dataset_root: str,
        image_col: str = "image_path",
        id_col: str = "sample_id",
        transform: Callable[[Any], Any] | None = None,
        max_items: int | None = None,
    ) -> None:
        if Image is None:  # pragma: no cover - depends on environment
            raise ImportError("Pillow is required to load images")

        df = pd.read_csv(manifest_csv, dtype=str, keep_default_na=False)
        if id_col not in df.columns:
            raise ValueError(f"id column '{id_col}' not found in manifest")
        if image_col not in df.columns:
            raise ValueError(f"image column '{image_col}' not found in manifest")

        if max_items is not None:
            df = df.head(max_items)

        self.samples: list[tuple[str, str]] = []
        for _, row in df.iterrows():
            sample_id = str(row[id_col])
            image_path = str(row[image_col])
            abs_path = resolve_image_path(dataset_root, image_path)
            self.samples.append((sample_id, abs_path))

        self.transform = transform if transform is not None else _default_transform()

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        sample_id, abs_path = self.samples[index]
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"image file not found: {abs_path}")

        with Image.open(abs_path) as source:
            image = source.convert("RGB")
            tensor = self.transform(image)

        return {
            "sample_id": sample_id,
            "image": tensor,
            "path": abs_path,
        }
