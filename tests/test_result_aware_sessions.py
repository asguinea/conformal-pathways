"""Information-flow and action/result state-machine checks, with no external data."""

import math
from copy import deepcopy

import pytest

from conformal_pathways.data import Observation, Sample
from conformal_pathways.sequential import DiagnosticScenario, SequentialSession, StageFilter
from conformal_pathways.sequential.engine import DIAGNOSTICS, POLICIES, ScoreConfig, select_action
from conformal_pathways.sequential.simulation import execute_policy
from conformal_pathways.workflows import Action, DRWorkflow, GlaucomaWorkflow
from conformal_pathways.workflows.core import DiagnosticResult


def entry():
    return Sample("case", "fixture", None).prediction_input()


def distribution(workflow):
    return (
        {"mild": 0.75, "severe": 0.25}
        if workflow.name == "dr_workflow"
        else {"low": 0.75, "high": 0.25}
    )


def session(workflow, thresholds=(math.inf,) * 3):
    return SequentialSession(
        workflow, entry(), distribution(workflow), StageFilter(workflow.name, thresholds)
    )


@pytest.mark.parametrize("workflow", [DRWorkflow(), GlaucomaWorkflow()])
@pytest.mark.parametrize("policy", POLICIES)
def test_delivered_result_changes_later_decisions_but_not_initial_decision(workflow, policy):
    decisions = []
    initial = []
    values = (False, True) if workflow.name == "dr_workflow" else ("low", "high")
    for value in values:
        run = session(workflow)
        initial.append(run.decision())
        test = Action(DIAGNOSTICS[workflow.name])
        run.choose(test)
        run.receive(DiagnosticResult(test.name, Observation(value, "measured_fixture", 1)))
        decisions.append(select_action(run.decision(), policy))
    assert initial[0] == initial[1]
    assert decisions[0] == Action("monitor")
    assert decisions[1].name in {"refer_retina", "refer_glaucoma"}


@pytest.mark.parametrize("workflow", [DRWorkflow(), GlaucomaWorkflow()])
def test_pending_test_blocks_decisions_until_explicit_result_and_rejects_replay(workflow):
    run = session(workflow)
    test = Action(DIAGNOSTICS[workflow.name])
    result = DiagnosticResult(test.name, Observation(None, "failed_test", 1))
    with pytest.raises(ValueError, match="no committed"):
        run.receive(result)
    run.choose(test)
    snapshot = (run.state, run.trace)
    for operation in (run.decision, lambda: run.choose(Action("monitor")), run.abstain):
        with pytest.raises(ValueError, match="awaiting_result"):
            operation()
    for bad in (None, {}, {"glaucoma_risk": "high"}):
        with pytest.raises(TypeError):
            run.receive(bad)
    for bad in (
        DiagnosticResult("wrong", result.observation),
        DiagnosticResult(test.name, Observation(None, "wrong_stage", 2)),
    ):
        with pytest.raises(ValueError, match="does not match"):
            run.receive(bad)
    assert (run.state, run.trace) == snapshot
    run.receive(result)
    assert run.decision().stage == 2
    assert run.state.get("observation_history")[0]["value"] is None
    key = "dme_status" if workflow.name == "dr_workflow" else "glaucoma_risk"
    assert run.state.get(key) == ("unknown" if workflow.name == "dr_workflow" else None)
    with pytest.raises(ValueError, match="no committed"):
        run.receive(result)


def test_unavailability_does_not_erase_explicit_prior_evidence():
    workflow = GlaucomaWorkflow()
    sample = Sample(
        "case",
        "fixture",
        None,
        observations={"glaucoma_risk": Observation("high", "prior_result", 0)},
    )
    run = SequentialSession(
        workflow,
        sample.prediction_input(),
        distribution(workflow),
        StageFilter(workflow.name, (math.inf,) * 3),
    )
    run.choose(Action("order_extra_tests"))
    run.receive(DiagnosticResult("order_extra_tests", Observation(None, "test_failed", 1)))
    assert run.state.get("glaucoma_risk") == "high"
    assert run.state.get("diagnostic_result_unavailable") is True


@pytest.mark.parametrize("policy", POLICIES)
def test_skip_never_queries_hidden_environment(policy):
    class ForbiddenEnvironment:
        workflow_name = "glaucoma_workflow"

        def result_for(self, *_):
            pytest.fail("skipped test read its hidden result")

    workflow = GlaucomaWorkflow()
    run = execute_policy(
        workflow,
        entry(),
        {"low": 1.0, "high": 0.0},
        StageFilter(workflow.name, (math.inf,) * 3),
        ForbiddenEnvironment(),
        policy,
    )
    assert run.actions[0] == Action("no_extra_tests")
    assert run.status == "complete"
    assert all(t["event"] != "result" for t in run.trace)
    with pytest.raises(ValueError):
        run.receive(DiagnosticResult("order_extra_tests", Observation("high", "late", 1)))


def test_hidden_labels_metadata_and_future_observations_cannot_change_decision():
    workflow = DRWorkflow()
    first = Sample("case", "fixture", None, {"dr_severity": "mild", "dme_positive": False})
    second = deepcopy(first)
    second.labels = {"dr_severity": "severe", "dme_positive": True}
    second.meta = {"dme_positive": True, "glaucoma_risk": "high"}
    second.observations = {"dme_positive": Observation(True, "future", 1)}
    stage_filter = StageFilter(workflow.name, (1.0, 0.8, 0.8))
    a, b = [
        SequentialSession(workflow, s.prediction_input(), distribution(workflow), stage_filter)
        for s in (first, second)
    ]
    assert a.decision() == b.decision()
    with pytest.raises(TypeError, match="label-free"):
        SequentialSession(workflow, first, distribution(workflow), stage_filter)


def test_input_output_mutations_cannot_modify_session_or_replay_finished_run():
    workflow = DRWorkflow()
    dist = distribution(workflow)
    thresholds = [2.0, 2.0, 2.0]
    stage_filter = StageFilter(workflow.name, thresholds)
    run = SequentialSession(workflow, entry(), dist, stage_filter)
    dist.update(mild=0.0, severe=1.0)
    thresholds[0] = 0.0
    decision = run.decision()
    decision.state.set("dme_status", "revealed_positive")
    decision.candidates[0][0].name = "corrupt"
    assert run.decision().candidates[0][0].name == "order_OCT"
    assert run.state.get("dme_status") == "unknown"
    run.choose(Action("no_OCT"))
    run.choose(Action("monitor"))
    action = Action("followup", {"weeks": 12})
    run.choose(action)
    action.params["weeks"] = 24
    trace = run.trace
    trace[0]["observed"]["dme_status"] = "corrupt"
    assert run.actions[-1].params["weeks"] == 12
    assert run.trace[0]["observed"]["dme_status"] == "unknown"
    with pytest.raises(ValueError, match="complete"):
        run.choose(action)


@pytest.mark.parametrize("thresholds,expected_stage", [((0.0, 0.0, 0.0), 1), ((1.0, 0.0, 0.0), 2)])
def test_empty_action_sets_abstain_at_the_actual_stage(thresholds, expected_stage):
    workflow = DRWorkflow()
    scenario = DiagnosticScenario(workflow.name, False, "fixture", "fixture-v1")
    run = execute_policy(
        workflow,
        entry(),
        distribution(workflow),
        StageFilter(workflow.name, thresholds),
        scenario,
        "min_stage_score",
    )
    assert run.status == "abstained"
    assert run.trace[-1]["stage"] == expected_stage
    assert len(run.actions) == expected_stage - 1
    with pytest.raises(ValueError, match="abstained"):
        run.decision()


def test_only_retained_actions_can_be_chosen_and_nonempty_sets_cannot_auto_abstain():
    run = session(DRWorkflow(), (1.0, 1.0, 1.0))
    for action in (Action("no_OCT"), Action("monitor"), Action("order_OCT", {"x": 1})):
        with pytest.raises(ValueError, match="not retained"):
            run.choose(action)
    with pytest.raises(ValueError, match="empty"):
        run.abstain()


@pytest.mark.parametrize("bad", [True, -1.0, -math.inf, math.nan])
def test_invalid_filter_inputs(bad):
    with pytest.raises(ValueError):
        StageFilter("dr_workflow", (bad, 1.0, 1.0))
    with pytest.raises(ValueError):
        ScoreConfig(bad, 1.0)


@pytest.mark.parametrize(
    "workflow,value",
    [
        ("dr_workflow", 1),
        ("dr_workflow", "true"),
        ("glaucoma_workflow", True),
        ("glaucoma_workflow", "unknown"),
    ],
)
def test_simulator_requires_normalized_values(workflow, value):
    with pytest.raises(ValueError, match="invalid potential"):
        DiagnosticScenario(workflow, value, "fixture", "fixture-v1")


@pytest.mark.parametrize("workflow", [DRWorkflow(), GlaucomaWorkflow()])
@pytest.mark.parametrize("policy", POLICIES)
def test_filter_ablation_does_not_change_selector_when_retained_actions_agree(workflow, policy):
    chosen = []
    for score in (ScoreConfig(1, 1), ScoreConfig(1, 0), ScoreConfig(0, 1)):
        run = SequentialSession(
            workflow,
            entry(),
            distribution(workflow),
            StageFilter(workflow.name, (math.inf,) * 3, score),
        )
        chosen.append(select_action(run.decision(), policy))
    assert chosen[0] == chosen[1] == chosen[2]
