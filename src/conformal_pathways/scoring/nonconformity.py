from __future__ import annotations

from conformal_pathways.workflows.core import Action, State


def _followup_weeks(action: Action) -> int | None:
    if action.name != "followup":
        return None
    weeks = action.params.get("weeks")
    return weeks if isinstance(weeks, int) else None


def rule_penalty_obs(workflow_name: str, stage: int, state: State, action: Action) -> float:
    if workflow_name == "dr_workflow":
        dme_status = state.get("dme_status")
        if stage == 1:
            if dme_status == "unknown" and action.name == "no_OCT":
                return 1.0
            if action.name == "order_OCT":
                return 0.0
            return 0.0
        if stage == 2:
            if dme_status == "revealed_positive" and action.name == "monitor":
                return 1.0
            return 0.0
        if stage == 3:
            if dme_status == "revealed_positive" and _followup_weeks(action) == 24:
                return 1.0
            return 0.0
        return 0.0

    if workflow_name == "glaucoma_workflow":
        glaucoma_risk = state.get("glaucoma_risk")
        if stage == 1:
            if glaucoma_risk == "high" and action.name == "no_extra_tests":
                return 1.0
            return 0.0
        if stage == 2:
            if glaucoma_risk == "high" and action.name == "monitor":
                return 1.0
            return 0.0
        if stage == 3:
            if glaucoma_risk == "high" and _followup_weeks(action) == 24:
                return 1.0
            return 0.0
        return 0.0

    return 0.0


def score_action(
    workflow_name: str,
    stage: int,
    state: State,
    action: Action,
    model_uncertainty: float,
    w_u: float = 1.0,
    w_r: float = 1.0,
) -> float:
    return w_u * model_uncertainty + w_r * rule_penalty_obs(
        workflow_name, stage, state, action
    )
