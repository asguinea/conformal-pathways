"""Toy-rule outcomes with explicit eligibility and abstention denominators."""

from __future__ import annotations

import math

from conformal_pathways.eval.selection_policies import (
    normalize_selection_policies,
    rank_pathways,
    select_pathway,
)
from conformal_pathways.safety.oracle import RULE_VERSION, is_safe, label_unavailability
from conformal_pathways.safety.oracle_policy import oracle_pathway


def pathway_key(pathway):
    return tuple((a.name, tuple(sorted(a.params.items()))) for a in pathway.actions)


def _validate(workflow, workflow_name, sample, paths):
    if workflow_name != workflow.name:
        raise ValueError("workflow_name mismatch")
    if len({pathway_key(p) for p in paths}) != len(paths):
        raise ValueError("duplicate candidate pathways")
    for p in paths:
        if len(p) != workflow.num_stages:
            raise ValueError("metrics require complete pathways")
        workflow.rollout(sample.observed_values(), p)
    return label_unavailability(workflow.name, sample.labels)


def _acceptable(workflow, sample, pathway):
    return is_safe(workflow.name, sample.labels, workflow.rollout({}, pathway), pathway)


def compute_sample_metrics(workflow, workflow_name, sample, prediction_set):
    reason = _validate(workflow, workflow_name, sample, prediction_set)
    size = len(prediction_set)
    eligible = reason is None
    outcomes = [_acceptable(workflow, sample, p) for p in prediction_set] if eligible else []
    count = sum(v is False for v in outcomes) if eligible else None
    return {
        "rule_version": RULE_VERSION,
        "rule_evaluable": eligible,
        "unavailable_reason": reason,
        "existential_safe": any(outcomes) if eligible else None,
        "oracle_retained": pathway_key(oracle_pathway(workflow, sample.labels))
        in {pathway_key(p) for p in prediction_set}
        if eligible
        else None,
        "set_size": size,
        "empty_set": size == 0,
        "unsafe_count": count,
        "any_unsafe": count > 0 if eligible and size else None,
        "unsafe_exposure": count / size if eligible and size else None,
    }


def _mean_record(values, name):
    usable = [v for v in values if v is not None]
    if any(not isinstance(v, (bool, int, float)) or not math.isfinite(v) for v in usable):
        raise ValueError(f"invalid values for {name}")
    numerator = sum(usable)
    denominator = len(usable)
    return {
        name: numerator / denominator if denominator else None,
        name + "__numerator": numerator,
        name + "__denominator": denominator,
        name + "__unavailable": len(values) - denominator,
    }


def aggregate_metrics(metrics_list):
    if not metrics_list:
        raise ValueError("metrics_list must be non-empty")
    result = {
        "n_samples": len(metrics_list),
        "rule_version": RULE_VERSION,
        "n_rule_evaluable": sum(
            row.get("rule_evaluable", row.get("existential_safe") is not None)
            for row in metrics_list
        ),
        "n_empty_sets": sum(row["empty_set"] for row in metrics_list),
    }
    result["n_rule_missing"] = result["n_samples"] - result["n_rule_evaluable"]
    for source, target in (
        ("existential_safe", "existential_safe"),
        ("oracle_retained", "oracle_retained"),
        ("set_size", "set_size"),
        ("empty_set", "empty_set_rate"),
        ("unsafe_exposure", "unsafe_exposure"),
        ("any_unsafe", "any_unsafe_rate"),
    ):
        result.update(_mean_record([r.get(source) for r in metrics_list], target))
    return result


def compute_chosen_path_metrics(
    prediction_set, workflow, workflow_name, sample, predictor=None, selection_policies=""
):
    reason = _validate(workflow, workflow_name, sample, prediction_set)
    result = {}
    for policy in normalize_selection_policies(selection_policies):
        selected = select_pathway(prediction_set, workflow, sample, predictor, policy)
        acceptable = (
            _acceptable(workflow, sample, selected)
            if selected is not None and reason is None
            else None
        )
        result.update(
            {
                f"chosen_is_safe__{policy}": acceptable,
                f"chosen_is_unsafe__{policy}": not acceptable if acceptable is not None else None,
                f"chosen_is_empty__{policy}": selected is None,
                f"chosen_label_missing__{policy}": reason is not None,
                f"chosen_error__{policy}": False,
            }
        )
    return result


def aggregate_chosen_path_metrics(rows):
    result = {}
    policies = {k.split("__", 1)[1] for r in rows for k in r if k.startswith("chosen_is_safe__")}
    for policy in sorted(policies):
        for source, target in (
            ("chosen_is_safe", "chosen_safe_rate"),
            ("chosen_is_unsafe", "chosen_unsafe_rate"),
            ("chosen_is_empty", "chosen_empty_rate"),
            ("chosen_label_missing", "chosen_label_missing_rate"),
            ("chosen_error", "chosen_error_rate"),
        ):
            result.update(
                _mean_record([r.get(f"{source}__{policy}") for r in rows], f"{target}__{policy}")
            )
    return result


def compute_topk_safety_metrics(
    prediction_set, workflow, workflow_name, sample, predictor=None, ranking_policies="", ks=(2, 3)
):
    reason = _validate(workflow, workflow_name, sample, prediction_set)
    if any(isinstance(k, bool) or not isinstance(k, int) or k < 1 for k in ks):
        raise ValueError("k must be a positive integer")
    result = {}
    for policy in normalize_selection_policies(ranking_policies):
        ranked = rank_pathways(prediction_set, workflow, sample, predictor, policy)
        for k in ks:
            chosen = ranked[:k]
            outcomes = [_acceptable(workflow, sample, p) for p in chosen] if reason is None else []
            result[f"top{k}_has_safe__{policy}"] = any(outcomes) if reason is None else None
            result[f"top{k}_all_safe__{policy}"] = (
                bool(chosen) and all(outcomes) if reason is None else None
            )
            result[f"top{k}_count__{policy}"] = len(chosen)
            result[f"top{k}_complete__{policy}"] = len(chosen) == k
    return result


def aggregate_topk_safety_metrics(per_sample_topk_metrics, ranking_policies, ks=(2, 3)):
    result = {}
    for policy in normalize_selection_policies(ranking_policies):
        for k in ks:
            for source, target in (
                ("has_safe", "has_safe_rate"),
                ("all_safe", "all_safe_rate"),
                ("count", "count_mean"),
                ("complete", "complete_rate"),
            ):
                result.update(
                    _mean_record(
                        [r.get(f"top{k}_{source}__{policy}") for r in per_sample_topk_metrics],
                        f"top{k}_{target}__{policy}",
                    )
                )
    return result
