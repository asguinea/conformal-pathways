"""Trace the exact score/threshold computation, with privileged outcomes separated."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path

from conformal_pathways.eval.metrics import pathway_key
from conformal_pathways.eval.selection_policies import (
    normalize_selection_policies,
    pathway_actions,
    select_pathway,
)
from conformal_pathways.safety.oracle import RULE_VERSION, is_safe, label_unavailability
from conformal_pathways.safety.oracle_policy import enumerate_all_pathways, oracle_pathway
from conformal_pathways.scoring.nonconformity import rule_penalty_obs, score_pathway


def parse_case_trace_ids(value):
    return {
        v.strip()
        for v in (value.split(",") if isinstance(value, str) else value or [])
        if v.strip()
    }


def _jsonify(value):
    if isinstance(value, float) and not math.isfinite(value):
        if value == math.inf:
            return "unbounded"
        raise ValueError("nonfinite trace value")
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


def export_case_trace(
    *,
    out_path,
    workflow,
    sample,
    predictor,
    alpha,
    alpha_allocation,
    stage_thresholds,
    selection_policies,
    pi,
    extra_context=None,
    w_u=1.0,
    w_r=1.0,
):
    thresholds = (
        stage_thresholds
        if isinstance(stage_thresholds, dict)
        else dict(enumerate(stage_thresholds, 1))
    )
    inputs = sample.prediction_input()
    paths = enumerate_all_pathways(workflow, inputs.observed_values())
    retained = {pathway_key(p) for p in pi}
    ids = {pathway_key(p): i for i, p in enumerate(paths)}
    entries = []
    for i, path in enumerate(paths):
        scores = score_pathway(workflow, inputs, predictor, path, w_u, w_r)
        state = workflow.initial_state(inputs.observed_values())
        stages = []
        for t, (action, score) in enumerate(zip(path.actions, scores, strict=True), 1):
            stages.append(
                {
                    "t": t,
                    "state": dict(state.observed),
                    "action": pathway_actions([action])[0],
                    "score": score,
                    "threshold": thresholds[t],
                    "kept": score <= thresholds[t],
                    "rule_penalty": rule_penalty_obs(workflow.name, t, state, action),
                }
            )
            state = workflow.transition(t, state, action, None)
        threshold_kept = all(s["kept"] for s in stages)
        in_pi = pathway_key(path) in retained
        entries.append(
            {
                "path_id": i,
                "actions": pathway_actions(path),
                "stage": stages,
                "retained": in_pi,
                "retained_in_pi": in_pi,
                "retained_by_thresholds": threshold_kept,
                "retained_mismatch": in_pi != threshold_kept,
                "oracle_safe": is_safe(workflow.name, sample.labels, state, path),
            }
        )
    selection = {}
    for policy in normalize_selection_policies(selection_policies):
        path = select_pathway(pi, workflow, sample, predictor, policy)
        pid = ids[pathway_key(path)] if path is not None else None
        selection[policy] = {
            "selected_path_id": pid,
            "selected_actions": pathway_actions(path) if path else None,
            "selected_oracle_safe": entries[pid]["oracle_safe"] if pid is not None else None,
        }
    reason = label_unavailability(workflow.name, sample.labels)
    reference = oracle_pathway(workflow, sample.labels) if reason is None else None
    trace = {
        "schema_version": 2,
        "rule_version": RULE_VERSION,
        "run": {
            "workflow_name": workflow.name,
            "alpha": alpha,
            "alpha_allocation": alpha_allocation,
            "protocol": "entry_observations_open_loop",
            "score_weights": {"model": w_u, "observed_rules": w_r},
        },
        "sample": {"sample_id": sample.sample_id, "dataset_source": sample.dataset_source},
        "entry_observations": {k: asdict(v) for k, v in inputs.observations.items()},
        "evaluation_only": {"labels": sample.labels, "unavailable_reason": reason},
        "thresholds": {f"stage{t}": q for t, q in thresholds.items()},
        "paths": entries,
        "retained_set": {
            "n_retained": len(pi),
            "retained_path_ids": [e["path_id"] for e in entries if e["retained"]],
            "retained_mismatch_count": sum(e["retained_mismatch"] for e in entries),
        },
        "selection": selection,
        "oracle_policy": {
            "oracle_selected_path_id": ids[pathway_key(reference)] if reference else None,
            "oracle_selected_actions": pathway_actions(reference) if reference else None,
        },
        "extra_context": extra_context or {},
    }
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_jsonify(trace), indent=2, allow_nan=False))
