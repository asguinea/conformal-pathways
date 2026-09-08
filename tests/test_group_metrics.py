from __future__ import annotations

from pathlib import Path

import pandas as pd

from conformal_pathways.eval.group_metrics import compute_group_metrics, main as group_metrics_main
from conformal_pathways.eval.runner import run_synthetic_experiment


def test_compute_group_metrics_and_worst_group_selection(tmp_path: Path) -> None:
    per_sample_path = tmp_path / "per_sample.csv"
    df = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "dataset_source": "toy",
                "dr_severity": "mild",
                "existential_safe": True,
                "unsafe_exposure": 0.1,
                "set_size": 3,
                "empty_set": False,
                "chosen_is_safe__guideline_first": True,
                "chosen_is_unsafe__guideline_first": False,
                "top2_has_safe__guideline_first": True,
                "top3_has_safe__guideline_first": True,
            },
            {
                "sample_id": "s2",
                "dataset_source": "toy",
                "dr_severity": "mild",
                "existential_safe": False,
                "unsafe_exposure": 0.9,
                "set_size": 1,
                "empty_set": True,
                "chosen_is_safe__guideline_first": False,
                "chosen_is_unsafe__guideline_first": True,
                "top2_has_safe__guideline_first": False,
                "top3_has_safe__guideline_first": False,
            },
            {
                "sample_id": "s3",
                "dataset_source": "toy",
                "dr_severity": "severe",
                "existential_safe": True,
                "unsafe_exposure": 0.0,
                "set_size": 4,
                "empty_set": False,
                "chosen_is_safe__guideline_first": True,
                "chosen_is_unsafe__guideline_first": False,
                "top2_has_safe__guideline_first": True,
                "top3_has_safe__guideline_first": True,
            },
        ]
    )
    df.to_csv(per_sample_path, index=False)

    group_df, worst_df = compute_group_metrics(
        per_sample_csv_path=str(per_sample_path),
        group_key="dr_severity",
        metric_specs=None,
    )

    mild_row = group_df.loc[group_df["dr_severity"] == "mild"].iloc[0]
    severe_row = group_df.loc[group_df["dr_severity"] == "severe"].iloc[0]
    assert mild_row["n"] == 2
    assert mild_row["existential_safe_rate"] == 0.5
    assert mild_row["chosen_unsafe_rate__guideline_first"] == 0.5
    assert severe_row["existential_safe_rate"] == 1.0

    # Safety metrics use min, risk metrics use max.
    assert worst_df.loc[0, "worst_group__existential_safe_rate"] == "mild"
    assert worst_df.loc[0, "worst_group__chosen_safe_rate__guideline_first"] == "mild"
    assert worst_df.loc[0, "worst_group__top2_has_safe_rate__guideline_first"] == "mild"
    assert worst_df.loc[0, "worst_group__chosen_unsafe_rate__guideline_first"] == "mild"
    assert worst_df.loc[0, "worst_group__unsafe_exposure_mean"] == "mild"
    assert worst_df.loc[0, "worst_group__empty_set_rate"] == "mild"


def test_emit_per_sample_csv_and_group_metrics_cli_smoke(tmp_path: Path) -> None:
    per_sample_path = tmp_path / "synthetic_per_sample.csv"
    _ = run_synthetic_experiment(
        workflow_name="dr_workflow",
        n=20,
        seed=0,
        alpha=0.1,
        selection_policies="guideline_first",
        emit_per_sample_csv=True,
        per_sample_csv_path=str(per_sample_path),
        subgroup_keys="dr_severity",
    )
    assert per_sample_path.exists()

    out_dir = tmp_path / "group_outputs"
    rc = group_metrics_main(
        [
            "--per_sample_csv",
            str(per_sample_path),
            "--group_key",
            "dr_severity",
            "--out_dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "synthetic_per_sample__groupby__dr_severity.csv").exists()
    assert (out_dir / "synthetic_per_sample__worstgroup__dr_severity.csv").exists()
