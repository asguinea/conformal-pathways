from __future__ import annotations

import re
from typing import Any

from conformal_pathways.data import Sample
from conformal_pathways.eval.selection_policies import (
    normalize_selection_policies,
    rank_pathways,
    select_pathway,
)
from conformal_pathways.safety import is_safe
from conformal_pathways.safety.oracle_policy import oracle_pathway
from conformal_pathways.workflows.core import Pathway, Workflow


def _freeze_value(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze_value(v)) for key, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(v) for v in value)
    if isinstance(value, set):
        return tuple(sorted((_freeze_value(v) for v in value), key=repr))
    if isinstance(value, (str, bytes, int, float, bool, type(None))):
        return value
    return repr(value)


def pathway_key(pathway: Pathway) -> tuple:
    return tuple(
        (
            action.name,
            tuple(sorted((key, _freeze_value(value)) for key, value in action.params.items())),
        )
        for action in pathway.actions
    )


def compute_sample_metrics(
    workflow: Workflow,
    workflow_name: str,
    sample: Sample,
    prediction_set: list[Pathway],
) -> dict[str, float | int | bool]:
    sample_meta = {**sample.labels, **sample.meta}

    oracle = oracle_pathway(workflow, sample_meta, safety_mode="strict")
    oracle_key = pathway_key(oracle)
    pred_keys = {pathway_key(pathway) for pathway in prediction_set}

    unsafe_count = 0
    existential_safe = False
    for pathway in prediction_set:
        final_state = workflow.rollout(sample_meta, pathway)
        safe = is_safe(workflow_name, sample_meta, final_state, pathway)
        if safe:
            existential_safe = True
        else:
            unsafe_count += 1

    set_size = len(prediction_set)
    empty_set = set_size == 0
    unsafe_exposure = 1.0 if empty_set else unsafe_count / set_size

    return {
        "existential_safe": existential_safe,
        "oracle_retained": oracle_key in pred_keys,
        "set_size": set_size,
        "empty_set": empty_set,
        "unsafe_exposure": unsafe_exposure,
    }


def _sanitize_policy_token(policy: str) -> str:
    token = re.sub(r"[^0-9A-Za-z]+", "_", policy).strip("_")
    return token or "policy"


def compute_chosen_path_metrics(
    prediction_set: list[Pathway],
    workflow: Workflow,
    workflow_name: str,
    sample: Sample,
    predictor: Any = None,
    selection_policies: str | list[str] = "",
) -> dict[str, bool]:
    """
    Compute per-sample chosen-path safety booleans for each selection policy.

    Empty prediction sets are treated conservatively:
    - chosen_is_empty = True
    - chosen_is_safe = False
    - chosen_is_unsafe = True
    """
    policy_names = normalize_selection_policies(selection_policies)
    if not policy_names:
        return {}

    sample_meta = {**sample.labels, **sample.meta}
    has_pathways = len(prediction_set) > 0
    outputs: dict[str, bool] = {}
    for policy_name in policy_names:
        policy_token = _sanitize_policy_token(policy_name)
        chosen_is_empty = False
        chosen_is_safe = False

        if not has_pathways:
            chosen_is_empty = True
        else:
            selected = None
            try:
                selected = select_pathway(
                    pi=prediction_set,
                    workflow=workflow,
                    sample=sample,
                    predictor=predictor,
                    policy=policy_name,
                )
            except Exception:
                selected = None

            if selected is None:
                chosen_is_empty = True
            else:
                final_state = workflow.rollout(sample_meta, selected)
                chosen_is_safe = bool(
                    is_safe(workflow_name, sample_meta, final_state, selected)
                )

        chosen_is_unsafe = not chosen_is_safe
        outputs[f"chosen_is_safe__{policy_token}"] = chosen_is_safe
        outputs[f"chosen_is_unsafe__{policy_token}"] = chosen_is_unsafe
        outputs[f"chosen_is_empty__{policy_token}"] = chosen_is_empty

    return outputs


def compute_topk_safety_metrics(
    prediction_set: list[Pathway],
    workflow: Workflow,
    workflow_name: str,
    sample: Sample,
    predictor: Any = None,
    ranking_policies: str | list[str] = "",
    ks: tuple[int, ...] = (2, 3),
) -> dict[str, bool]:
    """
    Compute per-sample top-k safety booleans for each ranking policy.

    Empty prediction sets yield top-k safety as False for all k.
    """
    policy_names = normalize_selection_policies(ranking_policies)
    if not policy_names:
        return {}

    sample_meta = {**sample.labels, **sample.meta}
    outputs: dict[str, bool] = {}
    for policy_name in policy_names:
        policy_token = _sanitize_policy_token(policy_name)
        try:
            ranked = rank_pathways(
                pi=prediction_set,
                workflow=workflow,
                sample=sample,
                predictor=predictor,
                policy=policy_name,
            )
        except Exception:
            ranked = []
        for k in ks:
            if k <= 0:
                continue
            topk = ranked[:k] if ranked else []
            topk_has_safe = False
            for pathway in topk:
                try:
                    final_state = workflow.rollout(sample_meta, pathway)
                    if is_safe(workflow_name, sample_meta, final_state, pathway):
                        topk_has_safe = True
                        break
                except Exception:
                    continue
            outputs[f"top{k}_has_safe__{policy_token}"] = topk_has_safe

    return outputs


def aggregate_topk_safety_metrics(
    per_sample_topk_metrics: list[dict[str, bool]],
    ranking_policies: str | list[str],
    ks: tuple[int, ...] = (2, 3),
) -> dict[str, float]:
    if not per_sample_topk_metrics:
        return {}

    policy_names = normalize_selection_policies(ranking_policies)
    if not policy_names:
        return {}

    n = len(per_sample_topk_metrics)
    outputs: dict[str, float] = {}
    for policy_name in policy_names:
        token = _sanitize_policy_token(policy_name)
        for k in ks:
            if k <= 0:
                continue
            key = f"top{k}_has_safe__{token}"
            outputs[f"top{k}_has_safe_rate__{token}"] = (
                sum(1.0 if row.get(key, False) else 0.0 for row in per_sample_topk_metrics)
                / n
            )

    return outputs


def aggregate_chosen_path_metrics(chosen_metrics_list: list[dict[str, bool]]) -> dict[str, float]:
    if not chosen_metrics_list:
        return {}

    n = len(chosen_metrics_list)
    policy_tokens: set[str] = set()
    for row in chosen_metrics_list:
        for key in row:
            if key.startswith("chosen_is_safe__"):
                policy_tokens.add(key.split("__", 1)[1])

    outputs: dict[str, float] = {}
    for token in sorted(policy_tokens):
        safe_key = f"chosen_is_safe__{token}"
        unsafe_key = f"chosen_is_unsafe__{token}"
        empty_key = f"chosen_is_empty__{token}"
        outputs[f"chosen_safe_rate__{token}"] = (
            sum(1.0 if row.get(safe_key, False) else 0.0 for row in chosen_metrics_list)
            / n
        )
        outputs[f"chosen_unsafe_rate__{token}"] = (
            sum(1.0 if row.get(unsafe_key, True) else 0.0 for row in chosen_metrics_list)
            / n
        )
        outputs[f"chosen_empty_rate__{token}"] = (
            sum(1.0 if row.get(empty_key, True) else 0.0 for row in chosen_metrics_list)
            / n
        )

    return outputs


def aggregate_metrics(metrics_list: list[dict]) -> dict[str, float]:
    if not metrics_list:
        raise ValueError("metrics_list must be non-empty")

    n = len(metrics_list)
    return {
        "existential_safe": sum(1.0 if m["existential_safe"] else 0.0 for m in metrics_list)
        / n,
        "oracle_retained": sum(1.0 if m["oracle_retained"] else 0.0 for m in metrics_list) / n,
        "set_size": sum(float(m["set_size"]) for m in metrics_list) / n,
        "empty_set_rate": sum(1.0 if m["empty_set"] else 0.0 for m in metrics_list) / n,
        "unsafe_exposure": sum(float(m["unsafe_exposure"]) for m in metrics_list) / n,
    }
