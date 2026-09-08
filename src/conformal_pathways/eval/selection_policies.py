"""Selection from open-loop candidate paths using entry observations only."""

from __future__ import annotations

from conformal_pathways.scoring.nonconformity import rule_penalty_obs, score_pathway
from conformal_pathways.workflows import Pathway

POLICIES = {"observed_rules_first", "min_rule_penalty", "min_total_score"}


def normalize_selection_policies(value):
    values = value.split(",") if isinstance(value, str) else list(value or [])
    policies = list(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))
    unknown = set(policies) - POLICIES
    if unknown:
        raise ValueError(
            f"unsupported selection policies {sorted(unknown)}; use {sorted(POLICIES)}"
        )
    return policies


def iter_pathways(pi):
    paths = list(pi.values()) if isinstance(pi, dict) else list(pi)
    if any(not isinstance(p, Pathway) for p in paths):
        raise TypeError("candidate sets must contain Pathway objects")
    return iter(paths)


def pathway_actions(pathway):
    actions = pathway.actions if isinstance(pathway, Pathway) else pathway
    return [
        a.name
        + (
            "(" + ",".join(f"{k}={v}" for k, v in sorted(a.params.items())) + ")"
            if a.params
            else ""
        )
        for a in actions
    ]


def render_pathway(pathway):
    return " -> ".join(pathway_actions(pathway)) if pathway is not None else "<abstain>"


def _penalty(pathway, workflow, inputs):
    state = workflow.initial_state(inputs.observed_values())
    total = 0.0
    for t, action in enumerate(pathway.actions, 1):
        total += rule_penalty_obs(workflow.name, t, state, action)
        state = workflow.transition(t, state, action, None)
    return total


def rank_pathways(pi, workflow, sample, predictor=None, policy="observed_rules_first"):
    normalize_selection_policies([policy])
    inputs = sample.prediction_input()
    paths = list(iter_pathways(pi))
    for p in paths:
        if len(p) != workflow.num_stages:
            raise ValueError("selection requires complete paths")
        workflow.rollout(inputs.observed_values(), p)

    def key(path):
        tie = tuple(pathway_actions(path))
        if policy == "min_total_score":
            if predictor is None:
                raise ValueError("min_total_score requires a fitted predictor")
            return (sum(score_pathway(workflow, inputs, predictor, path)), tie)
        penalty = _penalty(path, workflow, inputs)
        if policy == "min_rule_penalty":
            model_score = (
                sum(score_pathway(workflow, inputs, predictor, path))
                if predictor is not None
                else 0.0
            )
            return (penalty, model_score, tie)
        # Fixed burden/interval tie-breaks; never consult the privileged target.
        burden = sum(
            a.name in {"anti_VEGF", "treat", "refer_retina", "refer_glaucoma"} for a in path.actions
        )
        return (penalty, burden, abs(path.actions[-1].params["weeks"] - 12), tie)

    return sorted(paths, key=key)


def select_pathway(pi, workflow, sample, predictor=None, policy="observed_rules_first"):
    ranked = rank_pathways(pi, workflow, sample, predictor, policy)
    return ranked[0] if ranked else None
