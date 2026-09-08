from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Iterable

from conformal_pathways.scoring.nonconformity import rule_penalty_obs, score_action
from conformal_pathways.workflows.core import Action


def normalize_selection_policies(selection_policies: Any) -> list[str]:
    if selection_policies is None:
        return []
    if isinstance(selection_policies, str):
        items = [item.strip() for item in selection_policies.split(",")]
        return [item for item in items if item]
    if isinstance(selection_policies, (list, tuple, set)):
        return [str(item).strip() for item in selection_policies if str(item).strip()]
    value = str(selection_policies).strip()
    return [value] if value else []


def _is_pathway_candidate(value: Any) -> bool:
    if value is None:
        return False
    if hasattr(value, "actions"):
        return True
    if is_dataclass(value):
        return any(field.name == "actions" for field in fields(value))
    if isinstance(value, dict):
        return "actions" in value or all(isinstance(key, int) for key in value.keys())
    if isinstance(value, (list, tuple)):
        return True
    return False


def _action_to_text(action: Any) -> str:
    name = getattr(action, "name", None)
    params = getattr(action, "params", None)
    if isinstance(action, dict):
        name = action.get("name", name)
        params = action.get("params", params)
    elif isinstance(action, (list, tuple)) and action:
        name = action[0]
        params = action[1] if len(action) > 1 else None

    if isinstance(params, dict) and params:
        params_text = ", ".join(f"{k}={v!r}" for k, v in sorted(params.items()))
        return f"{name}({params_text})"
    if name is not None:
        return str(name)
    return str(action)


def _pathway_sort_key(pathway: Any) -> tuple[str, ...]:
    return tuple(pathway_actions(pathway))


def _coerce_pathways(pi: Any) -> list[Any]:
    if pi is None:
        return []

    if isinstance(pi, dict):
        values = list(pi.values())
        if values and all(_is_pathway_candidate(value) for value in values):
            return values
        keys = list(pi.keys())
        if keys and all(_is_pathway_candidate(key) for key in keys):
            return keys
        return []

    if is_dataclass(pi):
        for field in fields(pi):
            if field.name in {"pathways", "items", "values"}:
                value = getattr(pi, field.name, None)
                if isinstance(value, (list, tuple, set)):
                    return list(value)
        if hasattr(pi, "actions"):
            return [pi]

    if hasattr(pi, "pathways"):
        value = getattr(pi, "pathways", None)
        if isinstance(value, (list, tuple, set)):
            return list(value)

    if isinstance(pi, (list, tuple)):
        return list(pi)
    if isinstance(pi, set):
        return sorted(list(pi), key=_pathway_sort_key)

    if _is_pathway_candidate(pi):
        return [pi]
    return []


def iter_pathways(pi: Any) -> Iterable[Any]:
    pathways = _coerce_pathways(pi)
    if isinstance(pi, set):
        pathways = sorted(pathways, key=_pathway_sort_key)
    for pathway in pathways:
        yield pathway


def pathway_actions(pathway: Any) -> list[str]:
    actions: Any = None
    if hasattr(pathway, "actions"):
        actions = getattr(pathway, "actions", None)
    elif is_dataclass(pathway):
        if any(field.name == "actions" for field in fields(pathway)):
            actions = getattr(pathway, "actions", None)
    elif isinstance(pathway, dict):
        if "actions" in pathway:
            actions = pathway.get("actions")
        elif all(isinstance(key, int) for key in pathway.keys()):
            actions = [pathway[key] for key in sorted(pathway.keys())]
        else:
            actions = list(pathway.values())
    elif isinstance(pathway, (list, tuple)):
        actions = list(pathway)
    else:
        actions = [pathway]

    if actions is None:
        return []
    if not isinstance(actions, (list, tuple)):
        actions = [actions]
    return [_action_to_text(action) for action in actions]


def render_pathway(pathway: Any) -> str:
    parts = pathway_actions(pathway)
    return " -> ".join(parts) if parts else "<empty-pathway>"


def _as_action(action_like: Any) -> Action:
    if isinstance(action_like, Action):
        return action_like

    if hasattr(action_like, "name"):
        name = str(getattr(action_like, "name"))
        params = getattr(action_like, "params", {})
        if not isinstance(params, dict):
            params = {}
        return Action(name=name, params=dict(params))

    if isinstance(action_like, dict):
        name = str(action_like.get("name"))
        params = action_like.get("params", {})
        return Action(name=name, params=dict(params) if isinstance(params, dict) else {})

    if isinstance(action_like, (list, tuple)) and action_like:
        name = str(action_like[0])
        params: dict[str, Any] = {}
        if len(action_like) > 1 and isinstance(action_like[1], dict):
            params = dict(action_like[1])
        return Action(name=name, params=params)

    return Action(name=str(action_like), params={})


def _raw_actions(pathway: Any) -> list[Any]:
    if hasattr(pathway, "actions"):
        actions = getattr(pathway, "actions", None)
        if isinstance(actions, (list, tuple)):
            return list(actions)
        return []
    if isinstance(pathway, dict):
        if "actions" in pathway and isinstance(pathway["actions"], (list, tuple)):
            return list(pathway["actions"])
        if all(isinstance(key, int) for key in pathway.keys()):
            return [pathway[key] for key in sorted(pathway.keys())]
        return list(pathway.values())
    if isinstance(pathway, (list, tuple)):
        return list(pathway)
    return [pathway]


def _sample_meta(sample: Any) -> dict[str, Any]:
    if sample is None:
        return {}
    labels = getattr(sample, "labels", {})
    meta = getattr(sample, "meta", {})
    if isinstance(sample, dict):
        labels = sample.get("labels", labels)
        meta = sample.get("meta", meta)
    labels = labels if isinstance(labels, dict) else {}
    meta = meta if isinstance(meta, dict) else {}
    return {**labels, **meta}


def _workflow_name(workflow: Any) -> str:
    return str(getattr(workflow, "name", ""))


def _action_name(action: Any) -> str:
    if isinstance(action, Action):
        return action.name
    if hasattr(action, "name"):
        return str(getattr(action, "name"))
    if isinstance(action, dict):
        return str(action.get("name"))
    if isinstance(action, (list, tuple)) and action:
        return str(action[0])
    return str(action)


def _followup_weeks(pathway: Any) -> int:
    raw = _raw_actions(pathway)
    if not raw:
        return 10**9
    action = _as_action(raw[-1])
    if action.name != "followup":
        return 10**9
    weeks = action.params.get("weeks")
    return int(weeks) if isinstance(weeks, int) else 10**9


def _pathway_burden(pathway: Any) -> int:
    diagnostics = {"order_OCT", "order_extra_tests"}
    interventions = {"anti_VEGF", "refer_retina", "treat", "refer_glaucoma"}
    burden_names = diagnostics | interventions
    return sum(1 for action in _raw_actions(pathway) if _action_name(action) in burden_names)


def _matches_guideline_default(workflow_name: str, sample_meta: dict[str, Any], pathway: Any) -> bool:
    raw = _raw_actions(pathway)
    if len(raw) != 3:
        return False
    stage1 = _action_name(raw[0])
    stage2 = _action_name(raw[1])
    weeks = _followup_weeks(pathway)

    if workflow_name == "dr_workflow":
        if sample_meta.get("dme_positive") is True:
            return (
                stage1 == "order_OCT"
                and stage2 in {"anti_VEGF", "refer_retina"}
                and weeks == 4
            )
        if sample_meta.get("dme_positive") is False:
            return (
                stage1 in {"no_OCT", "order_OCT"}
                and stage2 == "monitor"
                and weeks == 12
            )
        return False

    if workflow_name == "glaucoma_workflow":
        if sample_meta.get("glaucoma_risk") == "high":
            return (
                stage1 == "order_extra_tests"
                and stage2 in {"treat", "refer_glaucoma"}
                and weeks == 4
            )
        return stage2 == "monitor" and weeks == 12

    return False


def _safe_uncertainty(predictor: Any, sample: Any) -> float:
    if predictor is None:
        return 0.0
    try:
        uncertainty = predictor.uncertainty([sample])[0]
        return float(uncertainty)
    except Exception:
        return 0.0


def _total_score(pathway: Any, workflow: Any, sample: Any, predictor: Any) -> float:
    sample_meta = _sample_meta(sample)
    workflow_name = _workflow_name(workflow)
    try:
        state = workflow.initial_state(sample_meta)
    except Exception:
        return float("inf")

    total = 0.0
    model_uncertainty = _safe_uncertainty(predictor, sample)
    for stage, raw_action in enumerate(_raw_actions(pathway), start=1):
        action = _as_action(raw_action)
        try:
            total += score_action(
                workflow_name=workflow_name,
                stage=stage,
                state=state,
                action=action,
                model_uncertainty=model_uncertainty,
                w_u=1.0,
                w_r=1.0,
            )
            state = workflow.transition(stage, state, action, sample_meta)
        except Exception:
            return float("inf")
    return total


def _total_rule_penalty(pathway: Any, workflow: Any, sample: Any) -> float:
    sample_meta = _sample_meta(sample)
    workflow_name = _workflow_name(workflow)
    try:
        state = workflow.initial_state(sample_meta)
    except Exception:
        return float("inf")

    total = 0.0
    for stage, raw_action in enumerate(_raw_actions(pathway), start=1):
        action = _as_action(raw_action)
        try:
            total += rule_penalty_obs(workflow_name, stage, state, action)
            state = workflow.transition(stage, state, action, sample_meta)
        except Exception:
            return float("inf")
    return total


def rank_pathways(
    pi: Any,
    workflow: Any,
    sample: Any,
    predictor: Any = None,
    policy: str = "guideline_first",
) -> list[Any]:
    pathways = list(iter_pathways(pi))
    if not pathways:
        return []

    workflow_name = _workflow_name(workflow)
    sample_meta = _sample_meta(sample)

    if policy == "guideline_first":
        return sorted(
            pathways,
            key=lambda pathway: (
                0 if _matches_guideline_default(workflow_name, sample_meta, pathway) else 1,
                _followup_weeks(pathway),
                _pathway_burden(pathway),
                tuple(pathway_actions(pathway)),
            ),
        )

    if policy == "min_total_score":
        return sorted(
            pathways,
            key=lambda pathway: (
                _total_score(pathway, workflow, sample, predictor),
                tuple(pathway_actions(pathway)),
            ),
        )

    if policy == "min_rule_penalty":
        return sorted(
            pathways,
            key=lambda pathway: (
                _total_rule_penalty(pathway, workflow, sample),
                (
                    _total_score(pathway, workflow, sample, predictor)
                    if predictor is not None
                    else float("inf")
                ),
                tuple(pathway_actions(pathway)),
            ),
        )

    raise ValueError(
        f"Unsupported selection policy '{policy}'. "
        "Expected one of: guideline_first, min_total_score, min_rule_penalty."
    )


def select_pathway(
    pi: Any,
    workflow: Any,
    sample: Any,
    predictor: Any = None,
    policy: str = "guideline_first",
) -> Any:
    ranked = rank_pathways(
        pi=pi,
        workflow=workflow,
        sample=sample,
        predictor=predictor,
        policy=policy,
    )
    if not ranked:
        raise ValueError("Cannot select pathway from empty prediction set")
    return ranked[0]
