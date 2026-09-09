"""Deployment boundary: entry evidence, committed actions, and delivered results only.

No labels, simulator, or retrospective reference policy enter this module.
The retained action sets define an implicit tree over possible future results.
An accepted action can lead to an empty downstream action set (abstention).
"""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import asdict, dataclass

from conformal_pathways.data.schema import PredictionInput
from conformal_pathways.scoring.nonconformity import (
    action_preferences,
    rule_penalty_obs,
    score_action,
)
from conformal_pathways.workflows.core import Action, DiagnosticResult, State, Workflow

ALGORITHM_VERSION = "result-aware-pathways-v1"
POLICIES = ("min_stage_score", "observed_rules_first")
DIAGNOSTICS = {"dr_workflow": "order_OCT", "glaucoma_workflow": "order_extra_tests"}


def action_key(action: Action) -> tuple:
    return action.name, tuple(sorted(action.params.items()))


@dataclass(frozen=True)
class ScoreConfig:
    w_u: float = 1.0
    w_r: float = 1.0

    def __post_init__(self):
        if any(
            isinstance(w, bool) or not math.isfinite(w) or w < 0 for w in (self.w_u, self.w_r)
        ) or not math.isfinite(self.w_u + self.w_r):
            raise ValueError("score weights must be finite nonnegative numbers")


@dataclass(frozen=True)
class StageFilter:
    """Fixed filters, shared without modification by calibration and execution.

    Construction alone makes no coverage claim. Use calibrate() with a fixed
    predictor and observation mechanism; see docs/sequential-method.md.
    """

    workflow_name: str
    thresholds: tuple[float, ...]
    score: ScoreConfig = ScoreConfig()

    def __post_init__(self):
        object.__setattr__(self, "thresholds", tuple(self.thresholds))
        if self.workflow_name not in DIAGNOSTICS or len(self.thresholds) != 3:
            raise ValueError("a supported three-stage workflow is required")
        if not isinstance(self.score, ScoreConfig):
            raise TypeError("score must be ScoreConfig")
        if any(isinstance(q, bool) or math.isnan(q) or q < 0 for q in self.thresholds):
            raise ValueError("thresholds must be nonnegative numbers or positive infinity")

    def to_dict(self):
        return {
            "workflow_name": self.workflow_name,
            "thresholds": ["infinity" if math.isinf(q) else q for q in self.thresholds],
            "score": asdict(self.score),
        }


def stage_scores(workflow, stage, state, distribution, config):
    preferences = action_preferences(workflow, stage, state, distribution)
    return [
        (
            action,
            score_action(
                workflow.name,
                stage,
                state,
                action,
                w_u=config.w_u,
                w_r=config.w_r,
                action_probability=preferences[action],
            ),
        )
        for action in workflow.actions_at(stage, state)
    ]


@dataclass(frozen=True)
class Decision:
    stage: int
    workflow_name: str
    state: State
    candidates: tuple[tuple[Action, float], ...]
    selection_scores: tuple[tuple[Action, float], ...]


def select_action(decision: Decision, policy: str = "min_stage_score") -> Action | None:
    """A fixed stage-local selector. Receives a detached visible-state snapshot."""
    if policy not in POLICIES:
        raise ValueError(f"unsupported sequential policy: {policy}")
    if not decision.candidates:
        return None
    fixed_scores = dict(decision.selection_scores)

    def rank(item):
        action, _ = item
        score = fixed_scores[action]
        if policy == "min_stage_score":
            return score, action_key(action)
        penalty = rule_penalty_obs(decision.workflow_name, decision.stage, decision.state, action)
        burden = action.name in {"anti_VEGF", "treat", "refer_retina", "refer_glaucoma"}
        followup_distance = abs(action.params.get("weeks", 12) - 12)
        return penalty, burden, followup_distance, score, action_key(action)

    return deepcopy(min(decision.candidates, key=rank)[0])


class SequentialSession:
    """Commit -> await a result -> update -> decide, for the two toy workflows.

    A diagnostic result (including explicit unavailability) is required before
    proceeding past an ordered test. Returned objects cannot mutate the session.
    This boundary prevents accidental leakage, not hostile Python introspection.
    """

    def __init__(
        self,
        workflow: Workflow,
        entry: PredictionInput,
        distribution: dict,
        stage_filter: StageFilter,
    ):
        if not isinstance(entry, PredictionInput):
            raise TypeError("entry must be a label-free PredictionInput")
        if workflow.name != stage_filter.workflow_name or workflow.num_stages != 3:
            raise ValueError("workflow and stage filter do not match")
        self._workflow = deepcopy(workflow)
        self._distribution = deepcopy(distribution)
        self._filter = stage_filter
        self._state = workflow.initial_state(entry.observed_values(stage=0))
        self._stage = 1
        self._pending = None
        self._actions = []
        self._trace = []
        self._status = "ready"
        # Validate the distribution even when every threshold is infinite.
        self.decision()

    @property
    def status(self):
        return self._status

    @property
    def state(self):
        return self._state.copy()

    @property
    def actions(self):
        return deepcopy(self._actions)

    @property
    def trace(self):
        return deepcopy(self._trace)

    def decision(self) -> Decision:
        if self._status != "ready":
            raise ValueError(f"no decision available while {self._status}")
        scores = stage_scores(
            self._workflow, self._stage, self._state, self._distribution, self._filter.score
        )
        candidates = tuple(
            (a, s) for a, s in scores if s <= self._filter.thresholds[self._stage - 1]
        )
        # Keep ranking fixed across filter ablations: changing calibration/set
        # weights must not silently change the policy used to compare the sets.
        fixed_scores = dict(
            stage_scores(
                self._workflow, self._stage, self._state, self._distribution, ScoreConfig()
            )
        )
        selection_scores = tuple((deepcopy(a), fixed_scores[a]) for a, _ in candidates)
        return Decision(
            self._stage, self._workflow.name, self.state, deepcopy(candidates), selection_scores
        )

    def choose(self, action: Action) -> None:
        decision = self.decision()
        if action not in [a for a, _ in decision.candidates]:
            raise ValueError("action is not retained at the current stage")
        action = deepcopy(action)
        previous = self.state
        updated = self._workflow.transition(self._stage, previous, action, None)
        self._trace.append(
            {
                "event": "decision",
                "stage": self._stage,
                "observed": deepcopy(previous.observed),
                "retained": [
                    {
                        "action": asdict(a),
                        "score": s,
                        "selection_score": dict(decision.selection_scores)[a],
                    }
                    for a, s in decision.candidates
                ],
                "chosen": asdict(action),
            }
        )
        self._actions.append(action)
        self._state = updated
        if self._stage == 1 and action.name == DIAGNOSTICS[self._workflow.name]:
            self._pending = (previous, action)
            self._status = "awaiting_result"
        else:
            self._advance()

    def receive(self, result: DiagnosticResult) -> None:
        if self._status != "awaiting_result":
            raise ValueError("no committed diagnostic is awaiting a result")
        if not isinstance(result, DiagnosticResult):
            raise TypeError("an explicit DiagnosticResult is required, including unavailability")
        previous, action = self._pending
        # Validate before changing state, so a failed delivery is recoverable.
        updated = self._workflow.transition(self._stage, previous, action, result)
        self._state = updated
        self._trace.append({"event": "result", "stage": self._stage, "result": asdict(result)})
        self._pending = None
        self._advance()

    def abstain(self) -> None:
        if self.decision().candidates:
            raise ValueError("automatic abstention requires an empty retained action set")
        self._trace.append(
            {
                "event": "abstention",
                "stage": self._stage,
                "observed": deepcopy(self._state.observed),
                "retained": [],
            }
        )
        self._status = "abstained"

    def _advance(self):
        self._stage += 1
        self._status = "complete" if self._stage > 3 else "ready"
