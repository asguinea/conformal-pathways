import json

import pandas as pd
import pytest

from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.experiment import evaluate_experiment
from conformal_pathways.eval.group_metrics import compute_group_metrics
from conformal_pathways.eval.metrics import (
    aggregate_chosen_path_metrics,
    aggregate_metrics,
    aggregate_topk_safety_metrics,
)
from conformal_pathways.eval.runner import make_synthetic_samples_dr, run_synthetic_experiment
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows import DRWorkflow


def test_finite_threshold_pipeline_exports_reaggregate_exactly(tmp_path):
    out = tmp_path / "cases.csv"
    result = run_synthetic_experiment(
        "dr_workflow",
        n=400,
        seed=17,
        alpha=0.3,
        selection_policies="observed_rules_first,min_total_score",
        emit_per_sample_csv=True,
        per_sample_csv_path=str(out),
        subgroup_keys="dr_severity",
    )
    frame = pd.read_csv(out)
    rows = frame.astype(object).where(frame.notna(), None).to_dict("records")
    recomputed = {
        **aggregate_metrics(rows),
        **aggregate_chosen_path_metrics(rows),
        **aggregate_topk_safety_metrics(rows, "observed_rules_first,min_total_score"),
    }
    for name, value in recomputed.items():
        if isinstance(value, (float, int)):
            assert result[name] == pytest.approx(value)
        else:
            assert result[name] == value
    assert result["n_cal_groups_evaluable"] < result["n_cal"]
    assert all(q != "unbounded" for q in result["calibration"]["thresholds"].values())
    assert set(frame.sample_id) == set(result["split_membership"]["test"])


def test_missing_evaluation_labels_are_retained_and_counted(tmp_path):
    samples = make_synthetic_samples_dr(100, 4)
    splits = make_splits(samples, 4)
    missing = splits["test"][0]
    next(s for s in samples if s.sample_id == missing).labels.pop("dme_positive")
    result = evaluate_experiment(
        DRWorkflow(),
        samples,
        splits,
        TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"]),
    )
    assert result["n_total"] == 100
    assert result["n_rule_missing"] == 1
    assert result["existential_safe__denominator"] == result["n_test"] - 1
    assert result["group_oracle_retained__unavailable"] == 1


def test_unpruned_pipeline_does_not_require_evaluable_calibration_labels():
    samples = make_synthetic_samples_dr(100, 4)
    splits = make_splits(samples, 4)
    for sample in samples:
        if sample.sample_id in splits["cal"]:
            sample.labels.pop("dme_positive")
    result = evaluate_experiment(
        DRWorkflow(),
        samples,
        splits,
        TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"]),
        variant="no_conformal",
    )
    assert result["set_size"] == 18
    assert result["n_cal_groups_evaluable"] == 0


def test_subgroup_missing_outcomes_have_zero_denominator(tmp_path):
    path = tmp_path / "groups.csv"
    pd.DataFrame(
        {
            "group": ["missing", "known"],
            "existential_safe": [None, True],
            "unsafe_exposure": [None, 0.0],
            "empty_set": [False, False],
            "set_size": [2, 2],
        }
    ).to_csv(path, index=False)
    grouped, worst = compute_group_metrics(str(path), "group")
    missing = grouped.set_index("group").loc["missing"]
    assert missing["existential_safe_rate__denominator"] == 0
    assert pd.isna(missing["existential_safe_rate"])
    assert worst.iloc[0]["worst_group__existential_safe_rate"] == "known"


def test_score_weight_ablation_trace_matches_actual_retention(tmp_path):
    samples = make_synthetic_samples_dr(400, 11)
    splits = make_splits(samples, 11)
    for variant in ("rules_only", "model_only", "no_conformal"):
        folder = tmp_path / variant
        evaluate_experiment(
            DRWorkflow(),
            samples,
            splits,
            TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"]),
            alpha=0.3,
            variant=variant,
            export_case_traces=splits["test"][:1],
            case_trace_out_dir=str(folder),
        )
        trace = json.loads(next(folder.glob("*.json")).read_text())
        assert trace["retained_set"]["retained_mismatch_count"] == 0
        assert trace["evaluation_only"]["labels"]
        assert trace["entry_observations"] == {}


def test_exports_distinguish_allocation_inputs_and_trace_subgroups(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    samples = make_synthetic_samples_dr(100, 4)
    splits = make_splits(samples, 4)
    outputs = []
    for allocation in ("uniform", "front_loaded"):
        result = evaluate_experiment(
            DRWorkflow(),
            samples,
            splits,
            TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"]),
            alpha_allocation=allocation,
            emit_per_sample_csv=True,
            export_case_traces=splits["test"][:1],
            case_trace_subgroup_keys="dr_severity",
        )
        outputs.append(result["per_sample_csv"])
    assert len(set(outputs)) == 2
    from pathlib import Path

    traces = list(Path("artifacts/qualitative").glob("*.json"))
    assert len(traces) == 2
    assert all(
        json.loads(p.read_text())["extra_context"]["evaluation_subgroups"]["dr_severity"]
        for p in traces
    )
    samples[0].dataset_source = "different_input_source"
    changed = evaluate_experiment(
        DRWorkflow(),
        samples,
        splits,
        TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"]),
        emit_per_sample_csv=True,
    )
    assert changed["per_sample_csv"] not in outputs


def test_explicit_splits_cannot_silently_discard_official_partition():
    samples = make_synthetic_samples_dr(100, 4)
    splits = make_splits(samples, 4)
    for sample in samples:
        sample.meta["split_hint"] = "train"
    with pytest.raises(ValueError, match="official partition"):
        evaluate_experiment(
            DRWorkflow(),
            samples,
            splits,
            TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"]),
        )


def test_allocation_summary_declares_run_denominators(tmp_path, monkeypatch):
    from conformal_pathways.eval import ablation_alpha_allocation as ablation

    def fake_grid(**kwargs):
        pd.DataFrame(
            {
                "alpha_allocation": ["uniform"] * 3,
                "existential_safe": [1.0, 0.0, None],
                "existential_safe__denominator": [1, 99, 0],
            }
        ).to_csv(kwargs["out_csv"], index=False)

    monkeypatch.setattr(ablation, "run_grid", fake_grid)
    output = ablation.run_ablation(
        "dr_workflow",
        "unused.csv",
        ".",
        "unused.npy",
        0.1,
        [1, 2, 3],
        "main",
        "",
        str(tmp_path / "summary.csv"),
    )
    row = pd.read_csv(output).iloc[0]
    assert row["summary_kind"] == "unweighted_mean_of_run_metrics"
    assert row["existential_safe"] == 0.5
    assert row["existential_safe__numerator"] == 1
    assert row["existential_safe__denominator"] == 2
    assert row["existential_safe__unavailable"] == 1
    assert row["n_runs"] == 3
