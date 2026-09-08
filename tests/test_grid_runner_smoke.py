from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("torch")
pytest.importorskip("torchvision")
PIL_Image = pytest.importorskip("PIL.Image")
pytest.importorskip("sklearn")

from conformal_pathways.eval.grid_runner import run_grid


def test_run_grid_smoke(tmp_path) -> None:
    root = tmp_path
    images_dir = root / "images"
    images_dir.mkdir(parents=True)

    rows = []
    severities = ["mild", "moderate", "severe", "mild", "moderate", "severe", "mild", "moderate"]
    dme_values = [True, False, True, False, True, False, True, False]
    for i in range(8):
        sample_id = f"s{i}"
        rel_path = f"images/{sample_id}.png"
        image = PIL_Image.new("RGB", (32, 32), color=(20 + i * 10, 40, 80))
        image.save(root / rel_path)
        rows.append(
            {
                "sample_id": sample_id,
                "dataset_source": "grid_ds",
                "image_path": rel_path,
                "dr_severity": severities[i],
                "dme_positive": dme_values[i],
                "patient_id": f"p{i}",
            }
        )

    manifest_csv = root / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_csv, index=False)
    out_csv = root / "results/grid.csv"

    alphas = [0.1]
    seeds = [0, 1]
    variants = ["main", "rules_only"]
    run_grid(
        workflow_name="dr_workflow",
        manifest_csv=str(manifest_csv),
        dataset_root=str(root),
        embeddings_out_path=str(root / "embeddings.npy"),
        out_csv=str(out_csv),
        alphas=alphas,
        seeds=seeds,
        variants=variants,
        batch_size=2,
        prefer_mps=False,
        filter_dme_subset=True,
    )

    assert out_csv.exists()
    results = pd.read_csv(out_csv)
    assert len(results) == len(alphas) * len(seeds) * len(variants)
    assert "alpha_allocation" in results.columns
    assert set(results["alpha_allocation"]) == {"uniform"}

    required_columns = {
        "workflow_name",
        "dataset",
        "alpha",
        "alpha_allocation",
        "seed",
        "variant",
        "existential_safe",
        "oracle_retained",
        "set_size",
        "empty_set_rate",
        "unsafe_exposure",
        "n_total",
        "n_train",
        "n_cal",
        "n_test",
    }
    assert required_columns.issubset(results.columns)
    assert not any(column.startswith("top2_has_safe_rate__") for column in results.columns)
    assert not any(column.startswith("top3_has_safe_rate__") for column in results.columns)
    assert not any(column.startswith("runtime_") for column in results.columns)


def test_run_grid_with_selection_policies_adds_chosen_columns(tmp_path) -> None:
    root = tmp_path
    images_dir = root / "images"
    images_dir.mkdir(parents=True)

    rows = []
    severities = ["mild", "moderate", "severe", "mild", "moderate", "severe", "mild", "moderate"]
    dme_values = [True, False, True, False, True, False, True, False]
    for i in range(8):
        sample_id = f"s{i}"
        rel_path = f"images/{sample_id}.png"
        image = PIL_Image.new("RGB", (32, 32), color=(30 + i * 10, 50, 90))
        image.save(root / rel_path)
        rows.append(
            {
                "sample_id": sample_id,
                "dataset_source": "grid_ds",
                "image_path": rel_path,
                "dr_severity": severities[i],
                "dme_positive": dme_values[i],
                "patient_id": f"p{i}",
            }
        )

    manifest_csv = root / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_csv, index=False)
    out_csv = root / "results/grid_selected.csv"
    per_sample_path = root / "results/per_sample.csv"

    run_grid(
        workflow_name="dr_workflow",
        manifest_csv=str(manifest_csv),
        dataset_root=str(root),
        embeddings_out_path=str(root / "embeddings.npy"),
        out_csv=str(out_csv),
        alphas=[0.1],
        seeds=[0],
        variants=["main"],
        batch_size=2,
        prefer_mps=False,
        filter_dme_subset=True,
        selection_policies="guideline_first,min_rule_penalty",
        emit_per_sample_csv=True,
        per_sample_csv_path=str(per_sample_path),
        subgroup_keys="dr_severity",
    )

    results = pd.read_csv(out_csv)
    assert "chosen_unsafe_rate__guideline_first" in results.columns
    assert "chosen_safe_rate__guideline_first" in results.columns
    assert "chosen_empty_rate__guideline_first" in results.columns
    assert "top2_has_safe_rate__guideline_first" in results.columns
    assert "top3_has_safe_rate__guideline_first" in results.columns
    assert per_sample_path.exists()


def test_run_grid_alpha_allocation_sweep(tmp_path) -> None:
    root = tmp_path
    images_dir = root / "images"
    images_dir.mkdir(parents=True)

    rows = []
    severities = ["mild", "moderate", "severe", "mild", "moderate", "severe", "mild", "moderate"]
    dme_values = [True, False, True, False, True, False, True, False]
    for i in range(8):
        sample_id = f"s{i}"
        rel_path = f"images/{sample_id}.png"
        image = PIL_Image.new("RGB", (32, 32), color=(50 + i * 10, 50, 50))
        image.save(root / rel_path)
        rows.append(
            {
                "sample_id": sample_id,
                "dataset_source": "grid_ds",
                "image_path": rel_path,
                "dr_severity": severities[i],
                "dme_positive": dme_values[i],
                "patient_id": f"p{i}",
            }
        )

    manifest_csv = root / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_csv, index=False)
    out_csv = root / "results/grid_alloc.csv"

    run_grid(
        workflow_name="dr_workflow",
        manifest_csv=str(manifest_csv),
        dataset_root=str(root),
        embeddings_out_path=str(root / "embeddings.npy"),
        out_csv=str(out_csv),
        alphas=[0.1],
        seeds=[0],
        variants=["main"],
        batch_size=2,
        prefer_mps=False,
        filter_dme_subset=True,
        alpha_allocations="uniform,front_loaded,back_loaded",
    )

    results = pd.read_csv(out_csv)
    assert len(results) == 3
    assert set(results["alpha_allocation"]) == {"uniform", "front_loaded", "back_loaded"}


def test_run_grid_profile_runtime_adds_runtime_columns(tmp_path) -> None:
    root = tmp_path
    images_dir = root / "images"
    images_dir.mkdir(parents=True)

    rows = []
    for i in range(8):
        sample_id = f"s{i}"
        rel_path = f"images/{sample_id}.png"
        image = PIL_Image.new("RGB", (32, 32), color=(60 + i * 10, 60, 60))
        image.save(root / rel_path)
        rows.append(
            {
                "sample_id": sample_id,
                "dataset_source": "grid_ds",
                "image_path": rel_path,
                "dr_severity": ["mild", "moderate", "severe", "mild", "moderate", "severe", "mild", "moderate"][i],
                "dme_positive": [True, False, True, False, True, False, True, False][i],
                "patient_id": f"p{i}",
            }
        )

    manifest_csv = root / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_csv, index=False)
    out_csv = root / "results/grid_runtime.csv"

    run_grid(
        workflow_name="dr_workflow",
        manifest_csv=str(manifest_csv),
        dataset_root=str(root),
        embeddings_out_path=str(root / "embeddings.npy"),
        out_csv=str(out_csv),
        alphas=[0.1],
        seeds=[0],
        variants=["main"],
        batch_size=2,
        prefer_mps=False,
        filter_dme_subset=True,
        profile_runtime=True,
    )

    results = pd.read_csv(out_csv)
    assert "runtime_ms_mean_per_sample" in results.columns
    assert "runtime_ms_p50_per_sample" in results.columns
    assert "runtime_ms_p95_per_sample" in results.columns
    assert "runtime_ms_total" in results.columns
    assert float(results.loc[0, "runtime_ms_mean_per_sample"]) >= 0.0
    assert float(results.loc[0, "runtime_ms_total"]) >= 0.0
