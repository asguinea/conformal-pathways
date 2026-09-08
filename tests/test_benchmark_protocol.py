"""Independent checks of experiment pairing, inference, uncertainty, and evidence integrity."""

import json
import math
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from conformal_pathways.benchmarks import runner
from conformal_pathways.benchmarks.provenance import digest, verify_files
from conformal_pathways.benchmarks.reporting import (
    compare_bundles,
    publish_bundles,
    read_bundle,
    verify_public_evidence,
)
from conformal_pathways.benchmarks.statistics import paired_summary, summarize_values
from conformal_pathways.benchmarks.synthetic import (
    FrozenPredictor,
    KnownSignalPredictor,
    generate_trial,
)
from conformal_pathways.data import Observation
from conformal_pathways.features.cache import sha256_file


@pytest.fixture
def config():
    path = Path(__file__).resolve().parents[1] / "experiments/batch3-v1.json"
    value = json.loads(path.read_text())
    value["synthetic"]["scenarios"] = value["synthetic"]["scenarios"][:1]
    value["synthetic"]["scenarios"][0].update(repetitions=2, train_groups=3, cal_groups=9)
    return value


def test_wilson_matches_published_nist_example_and_handles_zero_outcomes():
    result = summarize_values([1] * 26 + [0] * 174, confidence=0.90, binary=True)
    assert result["interval_low"] == pytest.approx(0.09577, abs=0.00001)
    zero = summarize_values([0] * 100, binary=True)
    assert zero["interval_high"] > 0
    assert summarize_values([None, None])["mean"] is None


def test_bounded_intervals_do_not_claim_certainty_from_constant_observations():
    values = [0.3] * 100
    result = summarize_values(values)
    radius = math.sqrt(math.log(40) / 200)
    assert result["interval_low"] == pytest.approx(0.3 - radius)
    assert result["interval_high"] == pytest.approx(0.3 + radius)
    real = summarize_values([0.0, 0.5, 1.0], independent=False)
    assert real["interval_low"] is None and real["observed_min"] == 0 and real["observed_max"] == 1
    with pytest.raises(ValueError, match="Bernoulli"):
        summarize_values([0.5], binary=True)


def test_pairing_uses_matched_repetitions_and_records_unavailability():
    result = paired_summary({0: 0.8, 1: None, 2: 0.4}, {0: 0.5, 1: 0.1, 2: 0.6})
    assert result["mean"] == pytest.approx(0.05)
    assert result["n_units"] == 2 and result["n_unavailable"] == 1
    with pytest.raises(ValueError, match="identical"):
        paired_summary({0: 1.0}, {1: 1.0})


def test_generator_has_known_disjoint_groups_and_repeatable_inputs(config):
    scenario = config["synthetic"]["scenarios"][0]
    samples, splits = generate_trial("dr_workflow", config["synthetic"], scenario, 8)
    again, second = generate_trial("dr_workflow", config["synthetic"], scenario, 8)
    assert samples == again and splits == second
    assert len({s.group_id() for s in samples}) == 13
    assert len(splits["test"]) == 2
    test = [s for s in samples if s.sample_id in splits["test"]]
    assert test[0].labels == test[1].labels
    assert test[0].observations != test[1].observations


def test_analytic_posterior_matches_likelihood_ratio_and_does_not_read_labels(config):
    model = KnownSignalPredictor("glaucoma_workflow", config["synthetic"])
    samples, _ = generate_trial(
        "glaucoma_workflow", config["synthetic"], config["synthetic"]["scenarios"][0], 6
    )
    samples[0].observations["signal"] = Observation(0.0, "test_measurement")
    value = model.predict_proba([samples[0].prediction_input()])[0]
    assert value["high"] == pytest.approx(0.35)
    samples[0].labels["glaucoma_risk"] = "arbitrary hidden value"
    assert model.predict_proba([samples[0].prediction_input()])[0] == value


def test_frozen_predictor_preserves_pairing_and_rejects_changed_training(config):
    samples, splits = generate_trial(
        "dr_workflow", config["synthetic"], config["synthetic"]["scenarios"][0], 7
    )
    training = [s for s in samples if s.sample_id in splits["train"]]
    frozen = FrozenPredictor(
        KnownSignalPredictor("dr_workflow", config["synthetic"]), training, samples
    )
    original = frozen.predict_proba([samples[-1].prediction_input()])
    original[0]["4"] = 0.0
    assert frozen.predict_proba([samples[-1].prediction_input()])[0]["4"] > 0
    modified = deepcopy(training)
    modified[0].labels["dr_severity"] = 9
    with pytest.raises(ValueError, match="training"):
        frozen.fit(modified)
    changed = deepcopy(samples[-1])
    changed.observations["signal"] = Observation(99.0, "other")
    with pytest.raises(ValueError, match="changed"):
        frozen.predict_proba([changed.prediction_input()])


def test_file_manifest_detects_mutation_and_path_escape(tmp_path):
    path = tmp_path / "input.txt"
    path.write_text("first")
    expected = {"input.txt": sha256_file(path)}
    verify_files(tmp_path, expected)
    path.write_text("second")
    with pytest.raises(ValueError, match="changed"):
        verify_files(tmp_path, expected)
    with pytest.raises(ValueError, match="outside"):
        verify_files(tmp_path, {"../outside": "invalid"})


def test_cloud_placeholder_rejected_before_reading_bytes(tmp_path, monkeypatch):
    from conformal_pathways.benchmarks.datasets import assert_local_images

    image = tmp_path / "image.jpg"
    image.write_bytes(b"fixture")
    original = Path.stat

    def fake_stat(path, *args, **kwargs):
        return (
            SimpleNamespace(st_flags=0x40000000)
            if path == image
            else original(path, *args, **kwargs)
        )

    monkeypatch.setattr(Path, "stat", fake_stat)
    with pytest.raises(RuntimeError, match="cloud-only"):
        assert_local_images(tmp_path)


def test_complete_run_reproduces_and_detects_changed_case_exports(config, tmp_path, monkeypatch):
    freeze = {"source_sha256": "test_fixture", "protocol_sha256": digest(config)}
    monkeypatch.setattr(runner, "verify_protocol", lambda _: (deepcopy(config), freeze))
    first, second = tmp_path / "first", tmp_path / "second"
    runner.run_suite("unused", "synthetic", first)
    runner.run_suite("unused", "synthetic", second)
    result = compare_bundles(first, second)
    assert result["all_scientific_records_exact"]
    execution, records = read_bundle(first)
    assert len(records) == len(runner.expected_contexts(config, "synthetic"))
    assert all(r["metrics"]["set_size"] == 18 for r in records)
    assert all("prediction_set_sha256" in (first / r["cases_path"]).read_text() for r in records)
    if pytest.importorskip("matplotlib"):
        output = tmp_path / "evidence"
        publish_bundles([first], output, allow_pending_real=True)
        assert verify_public_evidence(output)["trial_records"] == len(records)
        assert json.loads((output / "evidence.json").read_text())["pending_suites"] == ["real"]
    case = first / records[0]["cases_path"]
    case.write_text(case.read_text().replace("18", "17"))
    with pytest.raises(ValueError, match="changed"):
        read_bundle(first)


def test_failed_runs_are_retained_and_cannot_be_reported(config, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "verify_protocol", lambda _: (config, {"source_sha256": "test"}))

    def fail(*args):
        raise RuntimeError("deliberate fixture failure")

    monkeypatch.setattr(runner, "_synthetic", fail)
    with pytest.raises(RuntimeError, match="fixture failure"):
        runner.run_suite("unused", "synthetic", tmp_path / "failed")
    assert json.loads((tmp_path / "failed/execution.json").read_text())["status"] == "failed"
    with pytest.raises(ValueError, match="complete"):
        read_bundle(tmp_path / "failed")


def test_configuration_refuses_multiple_test_groups_for_bernoulli_analysis(config, tmp_path):
    from conformal_pathways.benchmarks.provenance import load_config

    config["synthetic"]["scenarios"][0]["test_groups"] = 2
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="one new test group"):
        load_config(path)


def test_paired_table_rejects_different_fitted_models():
    from conformal_pathways.benchmarks.reporting import aggregate_records

    base = {
        "suite": "synthetic",
        "cohort": "fixture",
        "workflow": "dr_workflow",
        "model": "class_prior",
        "repeat": 0,
        "input_sha256": "same-input",
        **{k: 1.0 for k in runner.METRICS},
    }
    rows = [
        {
            **base,
            "variant": variant,
            "alpha": None if variant == "no_conformal" else 0.1,
            "model_sha256": variant,
        }
        for variant in ("main", "model_only", "rules_only", "no_conformal")
    ]
    with pytest.raises(ValueError, match="fitted model"):
        aggregate_records(rows)


def test_real_run_cannot_start_without_sealed_inputs(config, tmp_path, monkeypatch):
    frozen = {"source_sha256": "test", "protocol_sha256": "test"}
    monkeypatch.setattr(runner, "verify_protocol", lambda _: (config, frozen))
    with pytest.raises(ValueError, match="not been sealed"):
        runner.run_suite(tmp_path / "protocol.json", "real", tmp_path / "run", tmp_path / "data")
    assert json.loads((tmp_path / "run/execution.json").read_text())["status"] == "failed"
