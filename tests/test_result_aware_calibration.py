"""Hand calculations and finite enumeration for reference-history retention."""

import math
from fractions import Fraction
from itertools import product

import pytest

from conformal_pathways.data import Sample
from conformal_pathways.safety.oracle import is_safe
from conformal_pathways.safety.oracle_policy import oracle_pathway
from conformal_pathways.sequential import DiagnosticScenario, SequentialSession, StageFilter
from conformal_pathways.sequential.calibration import calibrate
from conformal_pathways.sequential.engine import DIAGNOSTICS, ScoreConfig, action_key
from conformal_pathways.sequential.simulation import (
    execute_policy,
    proxy_scenarios,
    realized_prediction_set,
    reference_scores,
)
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow, Pathway


def dr(sid, positive=True, group=None, severity="mild"):
    return Sample(
        sid,
        "fixture",
        None,
        {"dr_severity": severity, "dme_positive": positive},
        {"patient_id": group or sid},
    )


def test_grouped_reference_scores_use_actual_post_test_state_and_report_exclusions():
    workflow = DRWorkflow()
    samples = [
        dr("a1", group="a"),
        dr("a2", False, "a"),
        dr("b"),
        dr("d", False),
        dr("c1", group="c"),
        dr("c2", None, "c"),
    ]
    dists = {s.sample_id: {"mild": 0.75, "severe": 0.25} for s in samples}
    fitted = calibrate(
        workflow, samples, dists, proxy_scenarios(workflow, samples), alpha=0.75, training_groups=()
    )
    # Positive reference: test=.75, then revealed-positive referral=0, follow-up=0.
    # Negative reference: skip=1.25, monitor=.25, follow-up=.25.
    assert fitted.scores == ((1.25, 0.75, 1.25), (0.25, 0.0, 0.25), (0.25, 0.0, 0.25))
    assert fitted.stage_filter.thresholds == (1.25, 0.25, 0.25)
    assert fitted.group_ids == tuple(samples[i].group_id() for i in (0, 2, 3))
    assert fitted.excluded_group_ids == (samples[-1].group_id(),)
    assert fitted.budgets == (0.25, 0.25, 0.25)


@pytest.mark.parametrize(
    "value,expected",
    [(True, (0.75, 0.0, 0.0)), (False, (0.75, 0.75, 0.75)), (None, (0.75, 0.75, 0.75))],
)
def test_noisy_and_unavailable_results_are_used_consistently_in_calibration(value, expected):
    workflow, sample = DRWorkflow(), dr("a")
    scenarios = {"a": DiagnosticScenario(workflow.name, value, "noisy_fixture", "noisy-v1")}
    fitted = calibrate(
        workflow, [sample], {"a": {"mild": 0.75, "severe": 0.25}}, scenarios, training_groups=()
    )
    assert tuple(v[0] for v in fitted.scores) == expected


@pytest.mark.parametrize("workflow", [DRWorkflow(), GlaucomaWorkflow()])
def test_exhaustive_reference_traversal_matches_session_and_tree(workflow):
    label_rows = (
        [
            {"dr_severity": grade, "dme_positive": positive}
            for grade, positive in product(range(5), [False, True])
        ]
        if workflow.name == "dr_workflow"
        else [{"glaucoma_risk": risk} for risk in ("low", "high")]
    )
    values = (False, True, None) if workflow.name == "dr_workflow" else ("low", "high", None)
    dist = (
        {"mild": 0.75, "severe": 0.25}
        if workflow.name == "dr_workflow"
        else {"low": 0.75, "high": 0.25}
    )
    for labels, value in product(label_rows, values):
        sample = Sample("s", "fixture", None, labels)
        scenario = DiagnosticScenario(workflow.name, value, "fixture", "fixture-v1")
        reference = oracle_pathway(workflow, labels)
        scores = reference_scores(
            workflow, sample.prediction_input(), dist, reference, scenario, ScoreConfig()
        )
        run = SequentialSession(
            workflow, sample.prediction_input(), dist, StageFilter(workflow.name, (math.inf,) * 3)
        )
        observed_scores = []
        for stage, action in enumerate(reference.actions, 1):
            observed_scores.append(dict(run.decision().candidates)[action])
            run.choose(action)
            if run.status == "awaiting_result":
                run.receive(scenario.result_for(stage, action))
        assert scores == observed_scores
        for thresholds in (
            (0.0, 0.0, 0.0),
            (0.75, 0.75, 0.75),
            (1.25, 0.25, 0.25),
            (math.inf,) * 3,
        ):
            stage_filter = StageFilter(workflow.name, thresholds)
            paths = realized_prediction_set(
                workflow, sample.prediction_input(), dist, stage_filter, scenario
            )
            keys = {tuple(action_key(a) for a in p.actions) for p in paths}
            retained = tuple(action_key(a) for a in reference.actions) in keys
            assert retained == all(s <= q for s, q in zip(scores, thresholds, strict=True))
            if thresholds == (math.inf,) * 3:
                assert len(paths) == len(keys) == 18


def test_reference_retention_does_not_imply_selected_path_acceptability():
    workflow = GlaucomaWorkflow()
    sample = Sample("high", "fixture", None, {"glaucoma_risk": "high"})
    scenario = DiagnosticScenario(workflow.name, "high", "perfect_fixture", "fixture-v1")
    stage_filter = StageFilter(workflow.name, (1.0, 1.0, 1.0))
    dist = {"low": 1.0, "high": 0.0}
    paths = realized_prediction_set(
        workflow, sample.prediction_input(), dist, stage_filter, scenario
    )
    reference = oracle_pathway(workflow, sample.labels)
    assert reference.actions in [p.actions for p in paths]
    run = execute_policy(
        workflow, sample.prediction_input(), dist, stage_filter, scenario, "min_stage_score"
    )
    assert run.actions[0].name != DIAGNOSTICS[workflow.name]
    assert is_safe(workflow.name, sample.labels, None, Pathway(run.actions)) is False


@pytest.mark.parametrize("alpha", [0.1, 0.3, 0.6])
def test_finite_exchangeable_group_enumeration_bounds_joint_reference_failure(alpha):
    # Uniformly hold out each complete group, including unequal group sizes and
    # correlated stages. This enumerates ranks; it is not empirical benchmarking.
    workflow = DRWorkflow()
    samples = [
        dr(f"{g}-{i}", bool((g + i) % 2), str(g), "severe" if g % 3 == 0 else "mild")
        for g in range(12)
        for i in range(1 + g % 2)
    ]
    scenarios = {
        s.sample_id: DiagnosticScenario(
            workflow.name,
            [True, False, None][int(s.meta["patient_id"]) % 3],
            "fixture",
            "fixture-v1",
        )
        for s in samples
    }
    dists = {
        s.sample_id: {
            "mild": (int(s.meta["patient_id"]) + 1) / 13,
            "severe": 1 - (int(s.meta["patient_id"]) + 1) / 13,
        }
        for s in samples
    }
    retained_groups = 0
    for group in range(12):
        calibration = [s for s in samples if s.meta["patient_id"] != str(group)]
        test = [s for s in samples if s.meta["patient_id"] == str(group)]
        fitted = calibrate(
            workflow,
            calibration,
            {s.sample_id: dists[s.sample_id] for s in calibration},
            {s.sample_id: scenarios[s.sample_id] for s in calibration},
            alpha=alpha,
            training_groups=(),
        )
        included = []
        for sample in test:
            scores = reference_scores(
                workflow,
                sample.prediction_input(),
                dists[sample.sample_id],
                oracle_pathway(workflow, sample.labels),
                scenarios[sample.sample_id],
                ScoreConfig(),
            )
            included.append(all(s <= q for s, q in zip(scores, fitted.stage_filter.thresholds)))
        retained_groups += all(included)
    assert Fraction(retained_groups, 12) >= 1 - Fraction(str(alpha))


def test_empty_eligibility_overlap_and_changed_mechanism_fail():
    workflow, sample = DRWorkflow(), dr("a")
    arguments = (workflow, [sample], {"a": {"mild": 1.0}}, proxy_scenarios(workflow, [sample]))
    with pytest.raises(ValueError, match="overlap"):
        calibrate(*arguments, training_groups=[sample.group_id()])
    with pytest.raises(ValueError, match="independently"):
        calibrate(*arguments, allocation="variance_weighted", training_groups=())
    sample.labels["dme_positive"] = None
    with pytest.raises(ValueError, match="no fully"):
        calibrate(*arguments, training_groups=())
