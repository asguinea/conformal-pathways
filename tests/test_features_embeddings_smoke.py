from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("torch")
pytest.importorskip("torchvision")
PIL_Image = pytest.importorskip("PIL.Image")

from conformal_pathways.features.extract_embeddings import (  # noqa: E402
    extract_embeddings_from_manifest,
)


def test_extract_embeddings_from_manifest_smoke(tmp_path) -> None:
    root = tmp_path
    images_dir = root / "images"
    images_dir.mkdir(parents=True)

    sample_ids = [f"s{i}" for i in range(4)]
    rel_paths = []
    for i, sample_id in enumerate(sample_ids):
        rel_path = f"images/{sample_id}.png"
        rel_paths.append(rel_path)
        image = PIL_Image.new("RGB", (32, 32), color=(i * 40, 10, 200 - i * 20))
        image.save(root / rel_path)

    manifest = pd.DataFrame({"sample_id": sample_ids, "image_path": rel_paths})
    manifest_path = root / "manifest.csv"
    manifest.to_csv(manifest_path, index=False)

    out_path = root / "embeddings.npy"
    stats = extract_embeddings_from_manifest(
        manifest_csv=str(manifest_path),
        dataset_root=str(root),
        out_path=str(out_path),
        batch_size=2,
        prefer_mps=False,
        weights="random",
        random_seed=0,
        device="cpu",
    )

    assert stats["n"] == 4
    assert stats["dim"] == 2048
    assert out_path.exists()

    arr = np.load(out_path)
    assert arr.shape == (4, 2048)

    ids_path = root / "embeddings_ids.txt"
    assert ids_path.exists()
    ids = ids_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(ids) == 4
