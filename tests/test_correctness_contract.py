"""Independent arithmetic, information-flow, and exhaustive toy-rule checks."""

import math
from copy import deepcopy
from fractions import Fraction
from itertools import product

import pandas as pd
import pytest

from conformal_pathways.conformal import build_prediction_set, collect_oracle_scores_by_stage
from conformal_pathways.conformal.thresholds import allocate_alpha, conformal_quantile
from conformal_pathways.data import Observation, Sample
from conformal_pathways.data.loaders import load_samples_from_csv
from conformal_pathways.data.splits import make_splits, validate_splits
from conformal_pathways.eval.metrics import (
    aggregate_chosen_path_metrics,
    aggregate_metrics,
    compute_chosen_path_metrics,
    compute_sample_metrics,
    pathway_key,
)
from conformal_pathways.eval.selection_policies import rank_pathways, select_pathway
from conformal_pathways.safety.oracle import is_safe
from conformal_pathways.safety.oracle_policy import oracle_pathway
from conformal_pathways.scoring.nonconformity import action_preferences
from conformal_pathways.workflows import Action, DRWorkflow, GlaucomaWorkflow, Pathway
from conformal_pathways.workflows.core import DiagnosticResult


class ObservedOnlyPredictor:
    def __init__(self, workflow="dr_workflow"):
        self.workflow = workflow
        self.inputs = []

    def predict_proba(self, inputs):
        for item in inputs:
            assert not hasattr(item, "labels")
            assert not hasattr(item, "meta")
            self.inputs.append(item)
        distribution = (
            {"mild": 0.75, "severe": 0.25}
            if self.workflow == "dr_workflow"
            else {"low": 0.75, "high": 0.25}
        )
        return [dict(distribution) for _ in inputs]


def record(sid="s", positive=True, severity="mild", group="p"):
    return Sample(
        sid,
        "synthetic",
        None,
        {"dr_severity": severity, "dme_positive": positive},
        {"patient_id": group},
    )


@pytest.mark.parametrize(
    "n,alpha", list(product(range(1, 21), [0.0, 0.01, 0.1, 0.2, 0.5, 0.8, 0.99]))
)
def test_quantile_against_rational_order_statistic(n, alpha):
    scores = list(reversed(range(n)))
    rank = math.ceil((n + 1) * (1 - Fraction(str(alpha))))
    expected = math.inf if rank == n + 1 else rank - 1
    assert conformal_quantile(scores, alpha) == expected


@pytest.mark.parametrize("alpha", [0.05, 0.1, 0.2, 0.5, 0.8])
def test_exchangeable_leave_one_out_rank_coverage(alpha):
    # Every rank is equally likely for the held-out unit. This checks exact
    # finite-sample frequencies, with and without ties, without random sampling.
    for values in ([0.0, 1.0, 2.0, 3.0, 4.0, 5.0], [0.0, 0.0, 1.0, 1.0, 2.0, 2.0]):
        retained = sum(
            value <= conformal_quantile(list(values[:i] + values[i + 1 :]), alpha)
            for i, value in enumerate(values)
        )
        assert Fraction(retained, len(values)) >= 1 - Fraction(str(alpha))


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, True])
def test_invalid_calibration_scores_rejected(bad):
    with pytest.raises(ValueError):
        conformal_quantile([0.0, bad], 0.1)


def test_zero_budget_is_unbounded_and_adaptive_budget_is_rejected():
    assert allocate_alpha(0.0, 3) == {1: 0.0, 2: 0.0, 3: 0.0}
    assert conformal_quantile([2.0, 3.0], 0.0) == math.inf
    with pytest.raises(ValueError, match="independently"):
        allocate_alpha(0.1, 3, "variance_weighted", {1: 1.0, 2: 1.0, 3: 1.0})


@pytest.mark.parametrize("workflow", [DRWorkflow(), GlaucomaWorkflow()])
def test_hidden_label_and_metadata_perturbations_cannot_change_sets_or_selection(workflow):
    first = record()
    second = deepcopy(first)
    if workflow.name == "dr_workflow":
        second.labels = {"dr_severity": "severe", "dme_positive": False}
    else:
        first.labels, second.labels = {"glaucoma_risk": "low"}, {"glaucoma_risk": "high"}
    second.meta.update(dme_positive=True, glaucoma_risk="high", dr_severity="severe")
    predictor = ObservedOnlyPredictor(workflow.name)
    thresholds = {1: 1.3, 2: 0.8, 3: 0.8}
    left = build_prediction_set(workflow, first, predictor, workflow.name, thresholds)
    right = build_prediction_set(workflow, second, predictor, workflow.name, thresholds)
    assert left and [pathway_key(p) for p in left] == [pathway_key(p) for p in right]
    for policy in ("observed_rules_first", "min_rule_penalty", "min_total_score"):
        assert rank_pathways(left, workflow, first, predictor, policy) == rank_pathways(
            right, workflow, second, predictor, policy
        )
    assert predictor.inputs


@pytest.mark.parametrize(
    "positive,expected",
    [(True, "revealed_positive"), (False, "revealed_negative"), (None, "unknown")],
)
def test_csv_result_is_only_revealed_by_explicit_executed_diagnostic(tmp_path, positive, expected):
    path = tmp_path / "manifest.csv"
    pd.DataFrame([{"sample_id": "001", "dr_severity": "mild", "dme_positive": positive}]).to_csv(
        path, index=False
    )
    sample = load_samples_from_csv(str(path), "ds", label_cols=["dr_severity", "dme_positive"])[0]
    assert sample.sample_id == "001"
    wf = DRWorkflow()
    initial = wf.initial_state(sample.observed_values())
    assert initial.get("dme_status") == "unknown"
    no_test = wf.transition(1, initial, Action("no_OCT"), None)
    assert no_test.get("dme_status") == "unknown"
    result = DiagnosticResult(
        "order_OCT", Observation(sample.labels.get("dme_positive"), "synthetic_proxy", 1)
    )
    observed = wf.transition(1, initial, Action("order_OCT"), result)
    assert observed.get("dme_status") == expected
    assert initial.get("dme_status") == "unknown"
    assert observed.get("observation_history")[0]["source"] == "synthetic_proxy"
    with pytest.raises((TypeError, ValueError)):
        wf.transition(1, initial, Action("no_OCT"), result)
    with pytest.raises(TypeError):
        wf.transition(1, initial, Action("order_OCT"), sample.labels)


def test_observed_results_change_action_preferences_without_claiming_online_coverage():
    wf = GlaucomaWorkflow()
    state = wf.initial_state({})
    dist = {"low": 0.9, "high": 0.1}
    before = action_preferences(wf, 2, state, dist)
    after_state = wf.transition(
        1,
        state,
        Action("order_extra_tests"),
        DiagnosticResult("order_extra_tests", Observation("high", "executed_simulator", 1)),
    )
    after = action_preferences(wf, 2, after_state, dist)
    assert before[Action("monitor")] == 0.9
    assert after[Action("monitor")] == 0.0
    assert after[Action("refer_glaucoma")] == 1.0


def test_future_observations_are_not_entry_inputs():
    sample = record()
    sample.observations["dme_positive"] = Observation(True, "later_result", 1)
    assert sample.prediction_input().observations == {}


@pytest.mark.parametrize("value", ["maybe", "unknown", "2", "-1"])
def test_invalid_boolean_labels_are_errors_not_missing_or_negative(tmp_path, value):
    path = tmp_path / "bad.csv"
    pd.DataFrame([{"sample_id": "s", "dme_positive": value}]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Boolean"):
        load_samples_from_csv(str(path), "d", label_cols=["dme_positive"])


def test_group_scores_use_maxima_and_exclude_incomplete_groups():
    samples = [
        record("a1", True, group="a"),
        record("a2", False, group="a"),
        record("b1", True, group="b"),
        record("c1", True, group="c"),
        record("c2", None, group="c"),
    ]
    result = collect_oracle_scores_by_stage(
        DRWorkflow(), samples, ObservedOnlyPredictor(), "dr_workflow"
    )
    assert result == {1: [1.25, 0.75], 2: [0.75, 0.75], 3: [0.75, 0.75]}


@pytest.mark.parametrize("severity,positive", list(product(range(5), [False, True])))
def test_all_dr_paths_against_independent_truth_table(severity, positive):
    wf = DRWorkflow()
    sample = record(severity=severity, positive=positive)
    paths = []
    for diagnostic, management, weeks in product(
        ["order_OCT", "no_OCT"], ["refer_retina", "anti_VEGF", "monitor"], [4, 12, 24]
    ):
        path = Pathway(
            [Action(diagnostic), Action(management), Action("followup", {"weeks": weeks})]
        )
        expected = not (
            (positive and diagnostic == "no_OCT")
            or ((positive or severity >= 3) and (management == "monitor" or weeks == 24))
            or (not positive and management == "anti_VEGF")
        )
        assert is_safe(wf.name, sample.labels, wf.rollout({}, path), path) is expected
        paths.append(path)
    assert len(paths) == 18
    reference = oracle_pathway(wf, sample.labels)
    assert is_safe(wf.name, sample.labels, wf.rollout({}, reference), reference) is True


@pytest.mark.parametrize("risk", ["low", "high"])
def test_all_glaucoma_paths_against_independent_truth_table(risk):
    wf = GlaucomaWorkflow()
    for diagnostic, management, weeks in product(
        ["order_extra_tests", "no_extra_tests"], ["treat", "refer_glaucoma", "monitor"], [4, 12, 24]
    ):
        path = Pathway(
            [Action(diagnostic), Action(management), Action("followup", {"weeks": weeks})]
        )
        expected = (
            (diagnostic == "order_extra_tests" and management != "monitor" and weeks != 24)
            if risk == "high"
            else management != "treat"
        )
        assert is_safe(wf.name, {"glaucoma_risk": risk}, wf.rollout({}, path), path) is expected


def test_selected_risk_denominator_excludes_abstention_and_missing_labels():
    wf = DRWorkflow()
    acceptable = Pathway(
        [Action("order_OCT"), Action("refer_retina"), Action("followup", {"weeks": 4})]
    )
    violating = Pathway([Action("no_OCT"), Action("monitor"), Action("followup", {"weeks": 24})])
    pairs = [
        (record("ok"), [acceptable]),
        (record("bad"), [violating]),
        (record("empty"), []),
        (record("missing", None), [acceptable]),
    ]
    rows = [
        compute_chosen_path_metrics(
            paths, wf, wf.name, sample, selection_policies="observed_rules_first"
        )
        for sample, paths in pairs
    ]
    rates = aggregate_chosen_path_metrics(rows)
    assert rates["chosen_unsafe_rate__observed_rules_first"] == 0.5
    assert rates["chosen_unsafe_rate__observed_rules_first__numerator"] == 1
    assert rates["chosen_unsafe_rate__observed_rules_first__denominator"] == 2
    assert rates["chosen_empty_rate__observed_rules_first"] == 0.25
    assert rates["chosen_label_missing_rate__observed_rules_first"] == 0.25
    sample_rows = [compute_sample_metrics(wf, wf.name, s, paths) for s, paths in pairs]
    rates = aggregate_metrics(sample_rows)
    assert rates["unsafe_exposure"] == 0.5
    assert rates["unsafe_exposure__denominator"] == 2
    assert rates["existential_safe"] == pytest.approx(1 / 3)
    assert sample_rows[2]["unsafe_exposure"] is None
    assert sample_rows[3]["existential_safe"] is None


def test_selection_failure_is_not_absorbed_as_abstention():
    wf = DRWorkflow()
    with pytest.raises(ValueError, match="unsupported"):
        compute_chosen_path_metrics([], wf, wf.name, record(), selection_policies="typo")
    assert select_pathway([], wf, record()) is None


@pytest.mark.parametrize("wf", [DRWorkflow(), GlaucomaWorkflow()])
def test_unbounded_baseline_equals_independent_cartesian_product_without_model(wf):
    sample = record()
    paths = build_prediction_set(wf, sample, None, wf.name, {1: math.inf, 2: math.inf, 3: math.inf})
    names = (
        (["order_OCT", "no_OCT"], ["refer_retina", "anti_VEGF", "monitor"])
        if wf.name == "dr_workflow"
        else (["order_extra_tests", "no_extra_tests"], ["treat", "refer_glaucoma", "monitor"])
    )
    expected = {(d, m, w) for d, m, w in product(*names, [4, 12, 24])}
    assert {
        (p.actions[0].name, p.actions[1].name, p.actions[2].params["weeks"]) for p in paths
    } == expected


def test_duplicate_ids_and_cross_split_groups_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        make_splits([record("same"), record("same")], 0)
    with pytest.raises(ValueError, match="group leakage"):
        validate_splits([record("a"), record("b")], {"train": ["a"], "cal": [], "test": ["b"]})
    a, b = record("a"), record("b")
    b.dataset_source = "different"
    assert a.group_id() != b.group_id()
    a.meta["global_patient_id"] = b.meta["global_patient_id"] = "shared"
    assert a.group_id() == b.group_id()


def test_official_test_membership_is_preserved_across_seeds():
    samples = [record(f"s{i}", group=f"p{i // 2}") for i in range(24)]
    for i, sample in enumerate(samples):
        sample.meta["split_hint"] = "train" if i < 20 else "test"
    for seed in range(5):
        splits = make_splits(samples, seed)
        assert set(splits["test"]) == {"s20", "s21", "s22", "s23"}
        validate_splits(samples, splits)


@pytest.mark.parametrize(
    "alpha,T", list(product([0.0, 0.1, 0.2, 0.3, 0.999999, 5e-324, 1e-323], range(1, 9)))
)
def test_allocations_never_exceed_budget_even_at_float_boundaries(alpha, T):
    from decimal import Decimal

    allocated = allocate_alpha(alpha, T)
    assert all(value >= 0 for value in allocated.values())
    assert sum(Decimal(str(v)) for v in allocated.values()) <= Decimal(str(alpha))


def test_calibration_rejects_known_training_group_overlap():
    from conformal_pathways.models import TrivialLabelPredictor

    train, cal = record("train", group="same_patient"), record("cal", group="same_patient")
    predictor = TrivialLabelPredictor("dr_severity", ["mild", "severe"])
    predictor.fit([train])
    with pytest.raises(ValueError, match="overlap"):
        collect_oracle_scores_by_stage(DRWorkflow(), [cal], predictor, "dr_workflow")
