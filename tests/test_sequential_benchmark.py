"""Generated-data checks for design completeness, paired controls and evidence integrity."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from conformal_pathways.benchmarks import sequential_runner as runner
from conformal_pathways.benchmarks.provenance import digest, write_json
from conformal_pathways.benchmarks.sequential_design import (
    diagnostic_scenarios,
    expected_contexts,
    load_config,
)
from conformal_pathways.benchmarks.sequential_reporting import (
    aggregate,
    compact,
    compare,
    read_bundle,
)
from conformal_pathways.benchmarks.synthetic import generate_trial
from conformal_pathways.workflows import DRWorkflow


def small_config():
    config = load_config(
        Path(__file__).resolve().parents[1] / "experiments/batch3-sequential-v1.json"
    )
    for scenario in config["synthetic"]["scenarios"]:
        scenario.update(repetitions=1, train_groups=3, cal_groups=3)
    return config


def test_complete_predeclared_design_counts():
    config = load_config(
        Path(__file__).resolve().parents[1] / "experiments/batch3-sequential-v1.json"
    )
    assert len(expected_contexts(config, "synthetic")) == 11392
    assert len(expected_contexts(config, "real")) == 400
    assert len({digest(c) for c in expected_contexts(config, "synthetic")}) == 11392


def test_missing_truth_is_separate_from_missing_diagnostic_and_group_results_are_shared():
    config = small_config()
    specification = config["synthetic"]["scenarios"][0]
    truth, splits = generate_trial("dr_workflow", config["synthetic"], specification, 7)
    masked, other_splits = generate_trial(
        "dr_workflow", config["synthetic"], {**specification, "missing_probability": 1.0}, 7
    )
    assert splits == other_splits
    assert [s.prediction_input() for s in truth] == [s.prediction_input() for s in masked]
    perfect = diagnostic_scenarios(
        DRWorkflow(), truth, 7, "perfect", config["mechanisms"]["perfect"]
    )
    assert all(s.value is not None for s in perfect.values())
    assert all("dme_positive" not in s.labels for s in masked)
    for a, b in zip(truth[::2], truth[1::2], strict=True):
        assert perfect[a.sample_id].value == perfect[b.sample_id].value
    wrong = diagnostic_scenarios(
        DRWorkflow(), truth, 7, "wrong", {"flip_probability": 1.0, "unavailable_probability": 0.0}
    )
    assert all(wrong[sid].value is not value.value for sid, value in perfect.items())
    absent = diagnostic_scenarios(
        DRWorkflow(), truth, 7, "absent", config["mechanisms"]["unavailable"]
    )
    assert all(s.value is None for s in absent.values())


def test_end_to_end_complete_controls_reaggregate_and_repeat(tmp_path, monkeypatch):
    config = small_config()
    monkeypatch.setattr(runner, "verify_protocol", lambda _: (config, {"source_sha256": "fixture"}))
    first, second = tmp_path / "first", tmp_path / "second"
    runner.run_suite("fixture.json", "synthetic", first)
    runner.run_suite("fixture.json", "synthetic", second)
    result = compare(first, second)
    assert result["status"] == "passed"
    execution, records = read_bundle(first)
    assert execution["actual_records"] == len(expected_contexts(config, "synthetic"))
    rows = [compact(r) for r in records]
    summary, pairs = aggregate(rows)
    assert summary and pairs
    assert any(p["comparator_mechanism"] == "entry_only" for p in pairs)
    assert any(p["comparator_mechanism"] == "unavailable" for p in pairs)
    assert any(p["comparator_variant"] == "model_only" for p in pairs)
    with pytest.raises(ValueError, match="empty output"):
        runner.run_suite("fixture.json", "synthetic", first)
    bad = deepcopy(rows)
    next(r for r in bad if r["variant"] == "model_only")["model_sha256"] = "changed"
    with pytest.raises(ValueError, match="fitted predictions"):
        aggregate(bad)
    # Even when file hashes are refreshed, dropping a comparison fails the design check.
    removed = next((second / "runs").glob("*.json"))
    removed.unlink()
    manifest = json.loads((second / "execution.json").read_text())
    manifest["files"].pop(str(removed.relative_to(second)))
    write_json(second / "execution.json", manifest)
    with pytest.raises(ValueError, match="missing, duplicate"):
        read_bundle(second)
