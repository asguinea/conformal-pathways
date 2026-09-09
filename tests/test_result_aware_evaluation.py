"""Integrated split/fit/reveal/evaluate checks and independently recomputed exports."""

import hashlib
import json
from copy import deepcopy

import pytest

from conformal_pathways.cli import main
from conformal_pathways.data import Observation, Sample
from conformal_pathways.safety.oracle import is_safe
from conformal_pathways.sequential import DiagnosticScenario, evaluate_sequential, proxy_scenarios
from conformal_pathways.sequential.engine import POLICIES
from conformal_pathways.workflows import Action, DRWorkflow, GlaucomaWorkflow, Pathway


class SpyPredictor:
    def __init__(self, workflow):
        self.workflow = workflow
        self.fits = []
        self.predictions = []

    def fit(self, samples):
        self.fits.append([s.sample_id for s in samples])

    def predict_proba(self, inputs):
        for entry in inputs:
            assert not hasattr(entry, "labels") and not hasattr(entry, "meta")
            assert all(o.stage == 0 for o in entry.observations.values())
            self.predictions.append(entry)
        dist = (
            {"mild": 0.75, "severe": 0.25}
            if self.workflow.name == "dr_workflow"
            else {"low": 0.75, "high": 0.25}
        )
        return [dict(dist) for _ in inputs]


def fixture(workflow):
    samples = []
    for i in range(24):
        labels = (
            {"dr_severity": "mild", "dme_positive": bool(i % 2)}
            if workflow.name == "dr_workflow"
            else {"glaucoma_risk": "high" if i % 2 else "low"}
        )
        samples.append(Sample(str(i), "fixture", None, labels, {"patient_id": str(i // 2)}))
    splits = {
        "train": [str(i) for i in range(4)],
        "cal": [str(i) for i in range(4, 20)],
        "test": [str(i) for i in range(20, 24)],
    }
    scenarios = proxy_scenarios(workflow, samples[4:])
    return samples, splits, scenarios


@pytest.mark.parametrize("workflow", [DRWorkflow(), GlaucomaWorkflow()])
@pytest.mark.parametrize("variant", ["main", "model_only", "rules_only", "no_conformal"])
def test_deterministic_full_pipeline_and_exports(workflow, variant):
    samples, splits, scenarios = fixture(workflow)
    predictor = SpyPredictor(workflow)
    report = evaluate_sequential(
        workflow, samples, splits, predictor, scenarios, variant=variant, alpha=0.75
    )
    repeat = evaluate_sequential(
        workflow, samples, splits, SpyPredictor(workflow), scenarios, variant=variant, alpha=0.75
    )
    assert report == repeat
    assert predictor.fits == [splits["train"]]
    assert [e.sample_id for e in predictor.predictions] == splits["cal"] + splits["test"]
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    payload = deepcopy(report)
    digest = payload.pop("report_sha256")
    assert (
        hashlib.sha256(
            json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        ).hexdigest()
        == digest
    )
    cases = report["cases"]
    for case in cases:
        details = case["evaluation_only"]
        assert details["path_toy_acceptable"] == [
            is_safe(
                workflow.name,
                details["truth_labels"],
                None,
                Pathway([Action(**action) for action in path]),
            )
            for path in details["realized_paths"]
        ]
    for policy in POLICIES:
        selected = [c["executions"][policy] for c in cases]
        for key in (
            "abstained",
            "completed",
            "diagnostic_ordered",
            "result_unavailable",
            "chosen_toy_violation",
            "label_unavailable",
        ):
            available = [s[key] for s in selected if s[key] is not None]
            record = report["metrics"]["policies"][policy][key]
            assert record == {
                "numerator": sum(available),
                "denominator": len(available),
                "unavailable": len(selected) - len(available),
                "value": sum(available) / len(available) if available else None,
            }
        for case in cases:
            execution = case["executions"][policy]
            if execution["completed"]:
                assert execution["actions"] in case["evaluation_only"]["realized_paths"]
            for i, event in enumerate(execution["trace"]):
                if event["event"] == "result":
                    assert execution["trace"][i - 1]["event"] == "decision"
                    assert (
                        execution["trace"][i - 1]["chosen"]["name"]
                        == event["result"]["action_name"]
                    )
    if variant == "no_conformal":
        assert report["calibration"] is None
        assert all(c["realized_set_size"] == 18 for c in cases)
    else:
        assert len(report["calibration"]["group_ids"]) == 8


def test_missing_labels_are_not_dropped_or_counted_as_success():
    workflow = DRWorkflow()
    samples, splits, scenarios = fixture(workflow)
    samples[4].labels["dme_positive"] = None
    samples[20].labels["dme_positive"] = None
    report = evaluate_sequential(workflow, samples, splits, SpyPredictor(workflow), scenarios)
    assert report["calibration"]["excluded_group_ids"] == [samples[4].group_id()]
    assert len(report["calibration"]["group_ids"]) == 7
    assert len(report["cases"]) == 4
    assert report["metrics"]["reference_retained"]["denominator"] == 3
    assert report["metrics"]["group_reference_retained"]["denominator"] == 1
    assert report["metrics"]["group_reference_retained"]["unavailable"] == 1
    for policy in POLICIES:
        assert report["cases"][0]["executions"][policy]["chosen_toy_violation"] is None
    for sample in samples[4:]:
        sample.labels["dme_positive"] = None
    with pytest.raises(ValueError, match="no fully"):
        evaluate_sequential(workflow, samples, splits, SpyPredictor(workflow), scenarios)
    unpruned = evaluate_sequential(
        workflow, samples, splits, SpyPredictor(workflow), scenarios, variant="no_conformal"
    )
    assert unpruned["metrics"]["reference_retained"]["value"] is None
    assert all(c["realized_set_size"] == 18 for c in unpruned["cases"])


def test_positive_negative_and_unavailable_results_change_execution_after_commitment():
    workflow = DRWorkflow()
    samples, splits, scenarios = fixture(workflow)
    reports = []
    for value in (True, False, None):
        altered = dict(scenarios)
        for sid in splits["test"]:
            altered[sid] = DiagnosticScenario(
                workflow.name, value, "fixture", "perfect-proxy-reveal-v1"
            )
        reports.append(
            evaluate_sequential(
                workflow, samples, splits, SpyPredictor(workflow), altered, variant="no_conformal"
            )
        )
    traces = [r["cases"][0]["executions"]["min_stage_score"]["trace"] for r in reports]
    assert traces[0][0] == traces[1][0] == traces[2][0]
    assert traces[0][2]["chosen"]["name"] == "refer_retina"
    assert traces[1][2]["chosen"]["name"] == traces[2][2]["chosen"]["name"] == "monitor"
    assert (
        reports[2]["metrics"]["policies"]["min_stage_score"]["result_unavailable"]["value"] == 1.0
    )


def test_test_truth_perturbation_cannot_change_execution_with_fixed_scenarios():
    workflow = GlaucomaWorkflow()
    samples, splits, scenarios = fixture(workflow)
    before = evaluate_sequential(workflow, samples, splits, SpyPredictor(workflow), scenarios)
    for sample in samples[20:]:
        sample.labels["glaucoma_risk"] = (
            "low" if sample.labels["glaucoma_risk"] == "high" else "high"
        )
        sample.meta["glaucoma_risk"] = sample.labels["glaucoma_risk"]
        sample.observations["glaucoma_risk"] = Observation("high", "future", 1)
    after = evaluate_sequential(workflow, samples, splits, SpyPredictor(workflow), scenarios)
    assert before["calibration"] == after["calibration"]
    assert before["provenance"]["entry_predictions"] == after["provenance"]["entry_predictions"]
    for old, new in zip(before["cases"], after["cases"], strict=True):
        for policy in POLICIES:
            assert old["executions"][policy]["trace"] == new["executions"][policy]["trace"]


def test_leakage_official_partition_and_scenario_mismatch_fail_before_fit():
    workflow = DRWorkflow()
    samples, splits, scenarios = fixture(workflow)
    predictor = SpyPredictor(workflow)
    invalid = deepcopy(splits)
    invalid["train"][0], invalid["test"][0] = invalid["test"][0], invalid["train"][0]
    with pytest.raises(ValueError, match="group leakage"):
        evaluate_sequential(workflow, samples, invalid, predictor, scenarios)
    for sample in samples:
        sample.meta["split_hint"] = "test" if sample.sample_id in splits["test"] else "train"
    invalid = deepcopy(splits)
    invalid["train"][:2], invalid["test"][:2] = invalid["test"][:2], invalid["train"][:2]
    with pytest.raises(ValueError, match="official partition"):
        evaluate_sequential(workflow, samples, invalid, predictor, scenarios)
    for invalid_scenarios in ({}, {**scenarios, "bad": scenarios["4"]}):
        with pytest.raises(ValueError, match="cover"):
            evaluate_sequential(workflow, samples, splits, predictor, invalid_scenarios)
    altered = {
        **scenarios,
        "20": DiagnosticScenario(workflow.name, None, "fixture", "different-v2"),
    }
    with pytest.raises(ValueError, match="mechanism"):
        evaluate_sequential(workflow, samples, splits, predictor, altered)
    assert predictor.fits == []
    report = evaluate_sequential(workflow, samples, splits, predictor, scenarios)
    assert report["config"]["split_protocol"] == "official_partition"


@pytest.mark.parametrize("workflow", ["dr", "glaucoma"])
def test_sequential_cli_offline_fixture_is_strict_json(workflow, capsys):
    assert main(["sequential-demo", "--workflow", workflow, "--n", "20"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["verification_scope"] == "installation_smoke_only"
    assert report["evaluation"]["algorithm_version"] == "result-aware-pathways-v1"
    assert len(report["evaluation"]["cases"]) > 0


def test_partial_abstentions_have_no_selected_violation_denominator():
    workflow = DRWorkflow()
    samples, splits, _ = fixture(workflow)
    for sample in samples[4:20]:
        sample.labels["dme_positive"] = True
    for sample in samples[20:]:
        sample.labels["dme_positive"] = False
    scenarios = proxy_scenarios(workflow, samples[4:])
    report = evaluate_sequential(
        workflow, samples, splits, SpyPredictor(workflow), scenarios, alpha=0.75
    )
    assert report["filter"]["thresholds"] == [0.75, 0.0, 0.0]
    assert report["metrics"]["reference_retained"]["numerator"] == 0
    assert report["metrics"]["realized_set_size"]["value"] == 0
    for policy in POLICIES:
        metrics = report["metrics"]["policies"][policy]
        assert metrics["abstained"] == {
            "value": 1.0,
            "numerator": 4,
            "denominator": 4,
            "unavailable": 0,
        }
        assert metrics["chosen_toy_violation"] == {
            "value": None,
            "numerator": 0,
            "denominator": 0,
            "unavailable": 4,
        }
        assert metrics["diagnostic_ordered"]["value"] == 1.0
        for case in report["cases"]:
            trace = case["executions"][policy]["trace"]
            assert [t["event"] for t in trace] == ["decision", "result", "abstention"]
            assert trace[-1]["stage"] == 2


def test_hand_calculated_selected_violations_are_distinct_from_retention():
    workflow = GlaucomaWorkflow()
    samples, splits, scenarios = fixture(workflow)
    report = evaluate_sequential(
        workflow, samples, splits, SpyPredictor(workflow), scenarios, alpha=0.75
    )
    assert report["metrics"]["reference_retained"]["value"] == 1.0
    assert report["metrics"]["existential_toy_acceptable"]["value"] == 1.0
    for policy in POLICIES:
        # Every selector skips, monitors and chooses 12 weeks. Two of four
        # held-out truth labels are high, so precisely those two violate the toy rule.
        assert report["metrics"]["policies"][policy]["chosen_toy_violation"] == {
            "value": 0.5,
            "numerator": 2,
            "denominator": 4,
            "unavailable": 0,
        }


def test_frozen_embedding_model_integrates_without_refitting_or_test_label_access(tmp_path):
    pytest.importorskip("sklearn")
    import numpy as np

    from conformal_pathways.benchmarks.synthetic import FrozenPredictor
    from conformal_pathways.features.cache import write_embedding_cache
    from conformal_pathways.models.embedding_predictor import EmbeddingLogRegPredictor

    workflow = GlaucomaWorkflow()
    samples, splits, scenarios = fixture(workflow)
    embeddings = np.random.default_rng(7).normal(size=(len(samples), 8)).astype(np.float32)
    path = tmp_path / "embeddings.npy"
    write_embedding_cache(
        path, embeddings, [s.sample_id for s in samples], {"kind": "generated_fixture", "seed": 7}
    )
    predictor = EmbeddingLogRegPredictor(
        str(path),
        str(tmp_path / "embeddings_ids.txt"),
        {s.sample_id: s.labels["glaucoma_risk"] for s in samples[:4]},
        ["low", "high"],
    )
    frozen = FrozenPredictor(predictor, samples[:4], samples)
    coefficients = predictor._model.coef_.copy()
    reports = [
        evaluate_sequential(workflow, samples, splits, frozen, scenarios, variant=v)
        for v in ("main", "model_only")
    ]
    assert set(predictor.label_map) == set(splits["train"])
    assert np.array_equal(coefficients, predictor._model.coef_)
    assert (
        reports[0]["provenance"]["entry_predictions"]
        == reports[1]["provenance"]["entry_predictions"]
    )
    assert len(reports[0]["cases"]) == 4
