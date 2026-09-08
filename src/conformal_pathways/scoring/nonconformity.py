"""Action-specific preference scores; not probabilities of clinical correctness."""

from __future__ import annotations

import math

from conformal_pathways.workflows.core import Action, State


def _followup_weeks(action):
    return action.params.get("weeks") if action.name == "followup" else None


def rule_penalty_obs(workflow_name: str, stage: int, state: State, action: Action) -> float:
    if workflow_name == "dr_workflow":
        status = state.get("dme_status", "unknown")
        severe = state.get("dr_severity") in {3, 4, "severe"}
        if stage == 1:
            return float(status != "revealed_negative" and action.name == "no_OCT")
        if stage == 2:
            return float(
                ((status == "revealed_positive" or severe) and action.name == "monitor")
                or (status == "revealed_negative" and action.name == "anti_VEGF")
            )
        if stage == 3:
            return float(
                (status == "revealed_positive" or severe) and _followup_weeks(action) == 24
            )
    elif workflow_name == "glaucoma_workflow":
        high = state.get("glaucoma_risk") == "high"
        if stage == 1:
            return float(high and action.name == "no_extra_tests")
        if stage == 2:
            return float(
                (high and action.name == "monitor")
                or (state.get("glaucoma_risk") == "low" and action.name == "treat")
            )
        if stage == 3:
            return float(high and _followup_weeks(action) == 24)
    else:
        raise ValueError(f"Unsupported workflow {workflow_name!r}")
    raise ValueError("stage must be 1, 2, or 3")


def action_preferences(workflow, stage, state, distribution):
    """Fixed projection of a label distribution into normalized action preferences.

    DR: severe-grade probability provides an escalation preference. Glaucoma:
    high-class probability does so. Explicit observations override this proxy.
    No hidden diagnostic outcome is assumed for a hypothetical future action.
    """
    if (
        not distribution
        or any(not math.isfinite(v) or v < 0 for v in distribution.values())
        or not math.isclose(sum(distribution.values()), 1, abs_tol=1e-8)
    ):
        raise ValueError("predictor probabilities must be finite, nonnegative, and sum to one")
    if workflow.name == "dr_workflow":
        allowed = {"0", "1", "2", "3", "4", "mild", "moderate", "severe"}
        if not set(distribution) <= allowed:
            raise ValueError("DR scoring requires a DR severity distribution")
        p = sum(v for k, v in distribution.items() if k in {"3", "4", "severe"})
        if state.get("dr_severity") is not None:
            from conformal_pathways.data.loaders import normalize_dr_severity

            p = float(normalize_dr_severity(state.get("dr_severity")) in {3, 4, "severe"})
        if state.get("dme_status") == "revealed_positive":
            p = 1.0
        diagnostic = "order_OCT"
        skip = "no_OCT"
        referral = "refer_retina"
        intervention = "anti_VEGF"
    elif workflow.name == "glaucoma_workflow":
        if not set(distribution) <= {"low", "high"}:
            raise ValueError("glaucoma scoring requires low/high probabilities")
        p = distribution.get("high", 0.0)
        if state.get("glaucoma_risk") in {"low", "high"}:
            p = float(state.get("glaucoma_risk") == "high")
        diagnostic, skip, referral, intervention = (
            "order_extra_tests",
            "no_extra_tests",
            "refer_glaucoma",
            "treat",
        )
    else:
        raise ValueError("unsupported workflow")
    if stage == 1:
        values = {diagnostic: p, skip: 1 - p}
    elif stage == 2:
        values = {referral: p, intervention: 0.0, "monitor": 1 - p}
    elif stage == 3:
        return {
            Action("followup", {"weeks": 4}): p,
            Action("followup", {"weeks": 12}): 1 - p,
            Action("followup", {"weeks": 24}): 0.0,
        }
    else:
        raise ValueError("invalid stage")
    return {Action(k): v for k, v in values.items()}


def score_action(
    workflow_name: str,
    stage: int,
    state: State,
    action: Action,
    model_uncertainty: float | None = None,
    w_u: float = 1.0,
    w_r: float = 1.0,
    *,
    action_probability: float | None = None,
) -> float:
    if model_uncertainty is not None:
        raise ValueError("scalar uncertainty scoring removed; supply action_probability")
    if (
        action_probability is None
        or not math.isfinite(action_probability)
        or not 0 <= action_probability <= 1
    ):
        raise ValueError("action_probability must be finite and in [0, 1]")
    if any(not math.isfinite(w) or w < 0 for w in (w_u, w_r)):
        raise ValueError("score weights must be finite and nonnegative")
    return w_u * (1 - action_probability) + w_r * rule_penalty_obs(
        workflow_name, stage, state, action
    )


def score_pathway(workflow, sample, predictor, pathway, w_u=1.0, w_r=1.0):
    inputs = sample.prediction_input() if hasattr(sample, "prediction_input") else sample
    state = workflow.initial_state(inputs.observed_values())
    outputs = predictor.predict_proba([inputs])
    if len(outputs) != 1:
        raise ValueError("predictor must return one distribution per input")
    scores = []
    for stage, action in enumerate(pathway.actions, 1):
        if action not in workflow.actions_at(stage, state):
            raise ValueError("invalid pathway action")
        preferences = action_preferences(workflow, stage, state, outputs[0])
        scores.append(
            score_action(
                workflow.name,
                stage,
                state,
                action,
                w_u=w_u,
                w_r=w_r,
                action_probability=preferences[action],
            )
        )
        state = workflow.transition(stage, state, action, None)
    return scores
