"""Offline potential results. Never pass these objects to a decision policy.

Each case has one pre-specified potential result for its stage-one diagnostic.
All counterfactual paths and selectors reuse it, including noisy/unavailable
results. This is a simulator assumption, not a recorded intervention outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

from conformal_pathways.data.schema import Observation, validate_samples
from conformal_pathways.workflows.core import Action, DiagnosticResult, Pathway

from .engine import DIAGNOSTICS, SequentialSession, StageFilter, select_action, stage_scores


@dataclass(frozen=True)
class DiagnosticScenario:
    workflow_name: str
    value: bool | str | None
    source: str
    mechanism: str

    def __post_init__(self):
        if self.workflow_name not in DIAGNOSTICS:
            raise ValueError("unsupported diagnostic workflow")
        if not isinstance(self.mechanism, str) or not self.mechanism.strip():
            raise ValueError("an explicit observation-mechanism identifier is required")
        Observation(self.value, self.source, 1)
        if self.workflow_name == "dr_workflow":
            valid = self.value is None or isinstance(self.value, bool)
        else:
            valid = self.value is None or (
                isinstance(self.value, str) and self.value in {"low", "high"}
            )
        if not valid:
            raise ValueError("invalid potential diagnostic result")

    def result_for(self, stage: int, action: Action) -> DiagnosticResult:
        if stage != 1 or action != Action(DIAGNOSTICS[self.workflow_name]):
            raise ValueError("a result can only be requested for the diagnostic action at stage 1")
        return DiagnosticResult(action.name, Observation(self.value, self.source, stage))


def proxy_scenarios(workflow, samples) -> dict[str, DiagnosticScenario]:
    """Explicit opt-in: simulate a perfect reveal of a held-back proxy label.

    Missing proxy labels produce unavailable results. This does not turn a
    severity/class label into an actual OCT, visual-field, or RNFL measurement.
    Custom scenarios should be supplied for error/missingness sensitivity work.
    """
    validate_samples(samples)
    key = {"dr_workflow": "dme_positive", "glaucoma_workflow": "glaucoma_risk"}[workflow.name]
    return {
        sample.sample_id: DiagnosticScenario(
            workflow.name,
            sample.labels.get(key),
            f"simulated_proxy:{key}",
            "perfect-proxy-reveal-v1",
        )
        for sample in samples
    }


def validate_scenarios(workflow, samples, scenarios):
    if set(scenarios) != {s.sample_id for s in samples}:
        raise ValueError("potential results must cover the supplied cases exactly once")
    if any(
        not isinstance(s, DiagnosticScenario) or s.workflow_name != workflow.name
        for s in scenarios.values()
    ):
        raise ValueError("scenario workflow mismatch")
    mechanisms = {s.mechanism for s in scenarios.values()}
    if len(mechanisms) != 1:
        raise ValueError("one pre-specified observation mechanism is required across cal/test")
    return next(iter(mechanisms))


def reference_scores(workflow, entry, distribution, path, scenario, config):
    """Privileged reference traversal; score before revealing each chosen test."""
    state = workflow.initial_state(entry.observed_values())
    if len(path) != workflow.num_stages:
        raise ValueError("a complete reference is required")
    scores = []
    for stage, action in enumerate(path.actions, 1):
        values = dict(stage_scores(workflow, stage, state, distribution, config))
        if action not in values:
            raise ValueError("inadmissible reference action")
        scores.append(values[action])
        result = (
            scenario.result_for(stage, action)
            if stage == 1 and action.name == DIAGNOSTICS[workflow.name]
            else None
        )
        state = workflow.transition(stage, state, action, result)
    return scores


def realized_prediction_set(workflow, entry, distribution, stage_filter, scenario):
    """Evaluator-only projection of the implicit tree onto one potential result.

    Returns complete action sequences compatible with this case's result.
    Counts are NOT numbers of adaptive policies, nor candidates visible at entry.
    The deployment selector must never receive this retrospective projection.
    """
    retained = []

    def walk(stage, state, path):
        if stage > workflow.num_stages:
            retained.append(path)
            return
        for action, score in stage_scores(workflow, stage, state, distribution, stage_filter.score):
            if score > stage_filter.thresholds[stage - 1]:
                continue
            result = (
                scenario.result_for(stage, action)
                if stage == 1 and action.name == DIAGNOSTICS[workflow.name]
                else None
            )
            walk(stage + 1, workflow.transition(stage, state, action, result), path.append(action))

    if stage_filter.workflow_name != workflow.name or scenario.workflow_name != workflow.name:
        raise ValueError("workflow mismatch")
    walk(1, workflow.initial_state(entry.observed_values()), Pathway())
    return retained


def execute_policy(workflow, entry, distribution, stage_filter: StageFilter, scenario, policy):
    if scenario.workflow_name != workflow.name:
        raise ValueError("scenario workflow mismatch")
    session = SequentialSession(workflow, entry, distribution, stage_filter)
    while session.status == "ready":
        decision = session.decision()
        action = select_action(decision, policy)
        if action is None:
            session.abstain()
            break
        session.choose(action)
        # Only now does the simulator deliver the case's hidden potential result.
        if session.status == "awaiting_result":
            session.receive(scenario.result_for(decision.stage, action))
    return session
