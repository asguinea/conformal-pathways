from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from conformal_pathways.eval.selection_policies import (
    iter_pathways,
    normalize_selection_policies,
    pathway_actions,
    select_pathway,
)
from conformal_pathways.safety import is_safe
from conformal_pathways.safety.oracle_policy import enumerate_all_pathways, oracle_pathway
from conformal_pathways.scoring.nonconformity import rule_penalty_obs, score_action


def parse_case_trace_ids(export_case_traces: str | list[str] | tuple[str, ...] | None) -> set[str]:
    if export_case_traces is None:
        return set()
    if isinstance(export_case_traces, str):
        items = [item.strip() for item in export_case_traces.split(",")]
        return {item for item in items if item}
    return {str(item).strip() for item in export_case_traces if str(item).strip()}


def _sample_labels(sample: Any) -> dict[str, Any]:
    labels = getattr(sample, "labels", {})
    if isinstance(sample, dict):
        labels = sample.get("labels", labels)
    return labels if isinstance(labels, dict) else {}


def _sample_meta(sample: Any) -> dict[str, Any]:
    meta = getattr(sample, "meta", {})
    if isinstance(sample, dict):
        meta = sample.get("meta", meta)
    return meta if isinstance(meta, dict) else {}


def _sample_value(sample: Any, key: str) -> Any:
    if hasattr(sample, key):
        return getattr(sample, key)
    if isinstance(sample, dict) and key in sample:
        return sample[key]
    labels = _sample_labels(sample)
    meta = _sample_meta(sample)
    if key in meta:
        return meta[key]
    if key in labels:
        return labels[key]
    return None


def _sample_meta_union(sample: Any) -> dict[str, Any]:
    return {**_sample_labels(sample), **_sample_meta(sample)}


def _action_text(action: Any) -> str:
    parts = pathway_actions([action])
    return parts[0] if parts else str(action)


def _pathway_key(pathway: Any) -> tuple[str, ...]:
    return tuple(pathway_actions(pathway))


def _thresholds_by_stage(stage_thresholds: list[float] | dict[int, float] | Any) -> dict[int, float]:
    if isinstance(stage_thresholds, dict):
        output: dict[int, float] = {}
        for key, value in stage_thresholds.items():
            try:
                stage = int(key)
                output[stage] = float(value)
            except Exception:
                continue
        return output
    if isinstance(stage_thresholds, (list, tuple)):
        return {idx: float(value) for idx, value in enumerate(stage_thresholds, start=1)}
    return {}


def _safe_uncertainty(predictor: Any, sample: Any) -> float:
    if predictor is None:
        return 0.0
    try:
        return float(predictor.uncertainty([sample])[0])
    except Exception:
        return 0.0


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonify(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def export_case_trace(
    *,
    out_path: str,
    workflow,
    sample,
    predictor,
    alpha: float,
    alpha_allocation: str,
    stage_thresholds: list[float] | dict[int, float],
    selection_policies: list[str] | str,
    pi,
    extra_context: dict | None = None,
) -> None:
    sample_meta = _sample_meta_union(sample)
    thresholds = _thresholds_by_stage(stage_thresholds)
    policy_names = normalize_selection_policies(selection_policies)
    extra_context = extra_context or {}

    subgroup_values = extra_context.get("subgroups", {})
    if not isinstance(subgroup_values, dict):
        subgroup_values = {}

    sample_payload: dict[str, Any] = {
        "sample_id": _sample_value(sample, "sample_id"),
        "dataset_source": _sample_value(sample, "dataset_source"),
        "patient_id": _sample_value(sample, "patient_id"),
        "eye_id": _sample_value(sample, "eye_id"),
    }
    for key, value in subgroup_values.items():
        sample_payload[key] = value

    run_payload = {
        "workflow_name": getattr(workflow, "name", "<unknown>"),
        "dataset": extra_context.get("dataset"),
        "alpha": alpha,
        "alpha_allocation": alpha_allocation,
        "variant": extra_context.get("variant"),
        "seed": extra_context.get("seed"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    candidate_paths = enumerate_all_pathways(workflow)
    pi_paths = list(iter_pathways(pi))
    pi_keys = {_pathway_key(pathway) for pathway in pi_paths}

    model_uncertainty = _safe_uncertainty(predictor, sample)
    path_entries: list[dict[str, Any]] = []
    path_id_by_key: dict[tuple[str, ...], int] = {}
    mismatch_count = 0

    for path_id, pathway in enumerate(candidate_paths):
        key = _pathway_key(pathway)
        path_id_by_key[key] = path_id
        state = workflow.initial_state(sample_meta)
        stage_entries: list[dict[str, Any]] = []
        retained_by_thresholds = True

        for t, action in enumerate(pathway.actions, start=1):
            rule_penalty = float(rule_penalty_obs(workflow.name, t, state, action))
            score = float(
                score_action(
                    workflow_name=workflow.name,
                    stage=t,
                    state=state,
                    action=action,
                    model_uncertainty=model_uncertainty,
                    w_u=1.0,
                    w_r=1.0,
                )
            )
            threshold = thresholds.get(t)
            kept = bool(threshold is not None and score <= threshold)
            retained_by_thresholds = retained_by_thresholds and kept
            stage_entries.append(
                {
                    "t": t,
                    "state_repr": repr(getattr(state, "observed", state)),
                    "action": _action_text(action),
                    "score": score,
                    "threshold": threshold,
                    "kept": kept,
                    "rule_penalty": rule_penalty,
                    "uncertainty": model_uncertainty,
                }
            )
            state = workflow.transition(t, state, action, sample_meta)

        oracle_safe = bool(is_safe(workflow.name, sample_meta, state, pathway))
        retained_in_pi = key in pi_keys
        retained_mismatch = retained_by_thresholds != retained_in_pi
        if retained_mismatch:
            mismatch_count += 1

        path_entries.append(
            {
                "path_id": path_id,
                "actions": pathway_actions(pathway),
                "stage": stage_entries,
                "retained": retained_in_pi,
                "retained_by_thresholds": retained_by_thresholds,
                "retained_in_pi": retained_in_pi,
                "retained_mismatch": retained_mismatch,
                "oracle_safe": oracle_safe,
            }
        )

    retained_ids = [entry["path_id"] for entry in path_entries if entry["retained_in_pi"]]

    selection_payload: dict[str, Any] = {}
    for policy_name in policy_names:
        try:
            selected = select_pathway(
                pi=pi,
                workflow=workflow,
                sample=sample,
                predictor=predictor,
                policy=policy_name,
            )
        except Exception:
            selected = None

        selected_id = None
        selected_actions = None
        selected_oracle_safe = None
        if selected is not None:
            selected_key = _pathway_key(selected)
            selected_id = path_id_by_key.get(selected_key)
            selected_actions = pathway_actions(selected)
            if selected_id is not None:
                selected_oracle_safe = path_entries[selected_id]["oracle_safe"]
            else:
                try:
                    final_state = workflow.rollout(sample_meta, selected)
                    selected_oracle_safe = bool(
                        is_safe(workflow.name, sample_meta, final_state, selected)
                    )
                except Exception:
                    selected_oracle_safe = None

        selection_payload[policy_name] = {
            "selected_path_id": selected_id,
            "selected_actions": selected_actions,
            "selected_oracle_safe": selected_oracle_safe,
        }

    oracle_selected_id = None
    oracle_selected_actions = None
    try:
        oracle_selected = oracle_pathway(workflow, sample_meta, safety_mode="strict")
        oracle_selected_actions = pathway_actions(oracle_selected)
        oracle_selected_id = path_id_by_key.get(_pathway_key(oracle_selected))
    except Exception:
        oracle_selected = None
        del oracle_selected

    trace_payload = {
        "run": run_payload,
        "sample": sample_payload,
        "thresholds": {f"stage{stage}": value for stage, value in sorted(thresholds.items())},
        "paths": path_entries,
        "retained_set": {
            "n_retained": len(retained_ids),
            "retained_path_ids": retained_ids,
            "retained_mismatch_count": mismatch_count,
        },
        "selection": selection_payload,
        "oracle_policy": {
            "oracle_selected_path_id": oracle_selected_id,
            "oracle_selected_actions": oracle_selected_actions,
        },
        "extra_context": _jsonify(extra_context),
    }

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(_jsonify(trace_payload), indent=2), encoding="utf-8")
