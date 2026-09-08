from __future__ import annotations

import pandas as pd

from conformal_pathways.data.loaders import filter_dme_labeled, load_samples_from_csv
from conformal_pathways.eval.run_from_manifest import run_evaluation_from_csv


def _write_dr_manifest(csv_path) -> None:
    rows = []
    severities = ["mild", "moderate", "severe"]
    for i in range(20):
        dme_positive = i % 3 == 0
        if i == 5:
            dme_positive = None
        rows.append(
            {
                "sample_id": f"s{i}",
                "image_path": f"/tmp/img_{i}.png",
                "dr_severity": severities[i % len(severities)],
                "dme_positive": dme_positive,
                "patient_id": f"p{i // 2}",
            }
        )

    pd.DataFrame(rows).to_csv(csv_path, index=False)


def test_run_evaluation_from_csv_dr_smoke(tmp_path) -> None:
    csv_path = tmp_path / "dr_manifest.csv"
    _write_dr_manifest(csv_path)

    metrics = run_evaluation_from_csv(
        workflow_name="dr_workflow",
        csv_path=str(csv_path),
        dataset_source="manifest_ds",
        label_cols=["dr_severity", "dme_positive"],
        meta_cols=["patient_id"],
        seed=11,
        alpha=0.1,
        filter_dme_subset=False,
    )

    for key in (
        "existential_safe",
        "oracle_retained",
        "set_size",
        "empty_set_rate",
        "unsafe_exposure",
    ):
        assert key in metrics

    assert 0.0 <= metrics["existential_safe"] <= 1.0
    assert 0.0 <= metrics["oracle_retained"] <= 1.0
    assert 0.0 <= metrics["empty_set_rate"] <= 1.0
    assert 0.0 <= metrics["unsafe_exposure"] <= 1.0


def test_filter_dme_subset_reduces_sample_count_when_missing_labels(tmp_path) -> None:
    csv_path = tmp_path / "dr_manifest_filter.csv"
    _write_dr_manifest(csv_path)

    loaded = load_samples_from_csv(
        csv_path=str(csv_path),
        dataset_source="manifest_ds",
        label_cols=["dr_severity", "dme_positive"],
        meta_cols=["patient_id"],
    )
    filtered = filter_dme_labeled(loaded)

    assert len(filtered) < len(loaded)
