from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("torch")
pytest.importorskip("torchvision")
PIL_Image = pytest.importorskip("PIL.Image")
pytest.importorskip("sklearn")

from conformal_pathways.eval.run_with_embeddings import run_evaluation_with_embeddings  # noqa: E402


def test_run_evaluation_with_embeddings_smoke(tmp_path) -> None:
    root = tmp_path
    images_dir = root / "images"
    images_dir.mkdir(parents=True)

    rows = []
    severities = ["mild", "moderate", "severe", "mild", "moderate", "severe"]
    dme_values = [True, False, True, False, True, False]
    for i in range(6):
        sample_id = f"s{i}"
        rel_path = f"images/{sample_id}.png"
        img = PIL_Image.new("RGB", (32, 32), color=(10 + i * 20, 40, 60))
        img.save(root / rel_path)
        rows.append(
            {
                "sample_id": sample_id,
                "dataset_source": "synthetic_dr",
                "image_path": rel_path,
                "dr_severity": severities[i],
                "dme_positive": dme_values[i],
                "patient_id": f"p{i}",
            }
        )

    manifest_path = root / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_path, index=False)

    embeddings_out_path = str(root / "embeddings.npy")
    metrics_1 = run_evaluation_with_embeddings(
        workflow_name="dr_workflow",
        manifest_csv=str(manifest_path),
        dataset_root=str(root),
        seed=0,
        alpha=0.1,
        embeddings_out_path=embeddings_out_path,
        batch_size=2,
        prefer_mps=False,
        weights="random",
        random_seed=0,
        device="cpu",
        filter_dme_subset=False,
    )
    assert (root / "embeddings.npy").exists()
    assert (root / "embeddings_ids.txt").exists()

    metrics_2 = run_evaluation_with_embeddings(
        workflow_name="dr_workflow",
        manifest_csv=str(manifest_path),
        dataset_root=str(root),
        seed=0,
        alpha=0.1,
        embeddings_out_path=embeddings_out_path,
        batch_size=2,
        prefer_mps=False,
        weights="random",
        random_seed=0,
        device="cpu",
        filter_dme_subset=False,
    )
    assert metrics_1 == metrics_2

    required = {
        "existential_safe",
        "oracle_retained",
        "set_size",
        "empty_set_rate",
        "unsafe_exposure",
    }
    assert required.issubset(metrics_1.keys())
    assert 0.0 <= metrics_1["existential_safe"] <= 1.0
    assert 0.0 <= metrics_1["oracle_retained"] <= 1.0
    assert 0.0 <= metrics_1["empty_set_rate"] <= 1.0
    assert 0.0 <= metrics_1["unsafe_exposure"] <= 1.0
    assert 0.0 <= metrics_1["set_size"] <= 18.0
