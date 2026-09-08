"""One evaluation implementation shared by synthetic and image-based runners."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from conformal_pathways.conformal import (
    build_prediction_set,
    collect_oracle_scores_by_stage,
    compute_stage_thresholds,
)
from conformal_pathways.conformal.thresholds import allocate_alpha
from conformal_pathways.data.splits import validate_splits
from conformal_pathways.eval.metrics import (
    _mean_record,
    aggregate_chosen_path_metrics,
    aggregate_metrics,
    aggregate_topk_safety_metrics,
    compute_chosen_path_metrics,
    compute_sample_metrics,
    compute_topk_safety_metrics,
)
from conformal_pathways.eval.per_sample_export import (
    _sample_lookup,
    build_per_sample_rows,
    default_per_sample_csv_path,
    make_run_tag,
    parse_subgroup_keys,
    write_per_sample_csv,
)
from conformal_pathways.eval.runtime import summarize_runtime_ms
from conformal_pathways.eval.selection_policies import normalize_selection_policies
from conformal_pathways.safety.oracle import label_unavailability

ALGORITHM_VERSION = "entry-pathways-v2"


def evaluate_experiment(
    workflow,
    samples,
    splits,
    predictor,
    *,
    alpha=0.1,
    alpha_allocation="uniform",
    variant="main",
    seed=0,
    selection_policies="",
    profile_runtime=False,
    emit_per_sample_csv=False,
    per_sample_csv_path=None,
    subgroup_keys="",
    export_case_traces="",
    case_trace_out_dir="artifacts/qualitative",
    case_trace_subgroup_keys="",
    debug_eval_introspection=False,
    debug_eval_introspection_exit=False,
    debug_print_selected_paths=False,
    w_u=None,
    w_r=None,
    split_protocol="random_groups",
):
    validate_splits(samples, splits)
    if split_protocol not in {"random_groups", "official_partition", "explicit_repartition"}:
        raise ValueError("unsupported split_protocol")
    if any(s.meta.get("split_hint") for s in samples) and split_protocol != "explicit_repartition":
        assigned = {sid: name for name, ids in splits.items() for sid in ids}
        has_cal = any(s.meta.get("split_hint") == "cal" for s in samples)
        for sample in samples:
            hint = sample.meta.get("split_hint")
            allowed = {"train", "cal"} if hint == "train" and not has_cal else {hint}
            if hint not in {"train", "cal", "test"} or assigned[sample.sample_id] not in allowed:
                raise ValueError(
                    "supplied splits violate official partition; explicit_repartition required"
                )
        split_protocol = "official_partition"
    if any(not splits[k] for k in splits):
        raise ValueError("insufficient split sizes for train/cal/test")
    if debug_eval_introspection_exit:
        raise ValueError("partial evaluation removed; enable introspection without early exit")
    weights = {
        "main": (1.0, 1.0),
        "model_only": (1.0, 0.0),
        "rules_only": (0.0, 1.0),
        "no_conformal": (1.0, 1.0),
    }
    if variant not in weights:
        raise ValueError(f"unsupported variant: {variant}")
    w_u = weights[variant][0] if w_u is None else w_u
    w_r = weights[variant][1] if w_r is None else w_r
    policies = normalize_selection_policies(selection_policies)
    lookup = {s.sample_id: s for s in samples}
    train, calibration, test = [
        [lookup[sid] for sid in splits[k]] for k in ("train", "cal", "test")
    ]
    predictor.fit(train)
    cal_groups = defaultdict(list)
    for s in calibration:
        cal_groups[s.group_id()].append(s)
    eligible_groups = [
        gid
        for gid, members in cal_groups.items()
        if all(label_unavailability(workflow.name, s.labels) is None for s in members)
    ]
    if variant == "no_conformal":
        thresholds = {t: float("inf") for t in range(1, workflow.num_stages + 1)}
        budgets = None
    else:
        scores = collect_oracle_scores_by_stage(
            workflow, calibration, predictor, workflow.name, w_u, w_r
        )
        thresholds = compute_stage_thresholds(scores, alpha, alpha_allocation)
        budgets = allocate_alpha(alpha, workflow.num_stages, alpha_allocation)
    input_digest = hashlib.sha256(
        json.dumps([asdict(s) for s in samples], sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    run_identity = {
        "algorithm_version": ALGORITHM_VERSION,
        "workflow": workflow.name,
        "input_sha256": input_digest,
        "splits": splits,
        "seed": seed,
        "variant": variant,
        "alpha": alpha,
        "alpha_allocation": alpha_allocation,
        "weights": [w_u, w_r],
        "policies": policies,
        "model": f"{type(predictor).__module__}.{type(predictor).__qualname__}",
        "model_config": {
            k: getattr(predictor, k, None)
            for k in ("C", "smoothing", "classes", "class_values", "label_key", "cache_metadata")
        },
    }
    run_id = hashlib.sha256(
        json.dumps(run_identity, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()[:20]
    run_tag = make_run_tag(workflow.name, seed, variant, alpha, alpha_allocation, run_id)
    rows, chosen_rows, top_rows, durations = [], [], [], []
    from conformal_pathways.eval.case_traces import export_case_trace, parse_case_trace_ids

    trace_ids = parse_case_trace_ids(export_case_traces)
    unknown_trace_ids = trace_ids - {s.sample_id for s in test}
    if unknown_trace_ids:
        raise ValueError(f"trace IDs are not in the test split: {sorted(unknown_trace_ids)}")
    for index, sample in enumerate(test):
        start = perf_counter()
        pi = build_prediction_set(workflow, sample, predictor, workflow.name, thresholds, w_u, w_r)
        row = compute_sample_metrics(workflow, workflow.name, sample, pi)
        chosen = compute_chosen_path_metrics(
            pi, workflow, workflow.name, sample, predictor, policies
        )
        top = compute_topk_safety_metrics(pi, workflow, workflow.name, sample, predictor, policies)
        rows.append({**row, **chosen, **top})
        chosen_rows.append(chosen)
        top_rows.append(top)
        durations.append((perf_counter() - start) * 1000)
        if debug_eval_introspection and index < 5:
            from conformal_pathways.eval.introspection import describe_prediction_set

            print(describe_prediction_set(pi, workflow, sample))
        if debug_print_selected_paths and index < 5:
            from conformal_pathways.eval.selection_policies import render_pathway, select_pathway

            for policy in policies:
                print(
                    f"[{policy}] selected: {render_pathway(select_pathway(pi, workflow, sample, predictor, policy))}"
                )
        if sample.sample_id in trace_ids:
            export_case_trace(
                out_path=str(
                    Path(case_trace_out_dir)
                    / f"{make_run_tag(run_tag, sample.sample_id, hashlib.sha256(sample.sample_id.encode()).hexdigest()[:12])}.json"
                ),
                workflow=workflow,
                sample=sample,
                predictor=predictor,
                alpha=alpha,
                alpha_allocation=alpha_allocation,
                stage_thresholds=thresholds,
                selection_policies=policies,
                pi=pi,
                w_u=w_u,
                w_r=w_r,
                extra_context={
                    "variant": variant,
                    "seed": seed,
                    "run_id": run_id,
                    "evaluation_subgroups": {
                        k: _sample_lookup(sample, k)
                        for k in parse_subgroup_keys(case_trace_subgroup_keys)
                    },
                },
            )
    result = aggregate_metrics(rows)
    if policies:
        result.update(aggregate_chosen_path_metrics(chosen_rows))
        result.update(aggregate_topk_safety_metrics(top_rows, policies))
    grouped_test = defaultdict(list)
    for sample, row in zip(test, rows, strict=True):
        grouped_test[sample.group_id()].append(row["oracle_retained"])
    group_inclusions = [
        all(values) if all(v is not None for v in values) else None
        for values in grouped_test.values()
    ]
    result.update(_mean_record(group_inclusions, "group_oracle_retained"))
    result.update(
        {
            "algorithm_version": ALGORITHM_VERSION,
            "protocol": "entry_observations_open_loop",
            "run_id": run_id,
            "input_sha256": input_digest,
            "variant": variant,
            "alpha": alpha if variant != "no_conformal" else None,
            "alpha_allocation": alpha_allocation,
            "n_total": len(samples),
            "n_train": len(train),
            "n_cal": len(calibration),
            "n_test": len(test),
            "n_cal_groups_total": len(cal_groups),
            "n_cal_groups_evaluable": len(eligible_groups),
            "n_cal_groups_excluded": len(cal_groups) - len(eligible_groups),
            "split_membership": splits,
            "split_protocol": split_protocol,
            "calibration": {
                "used_for_thresholds": variant != "no_conformal",
                "unit": "declared_group_max",
                "group_ids": sorted(eligible_groups),
                "stage_budgets": budgets,
                "thresholds": {
                    str(t): q if q != float("inf") else "unbounded" for t, q in thresholds.items()
                },
                "score_weights": {"model": w_u, "observed_rules": w_r},
            },
            "coverage_assumptions_verified_on_dataset": False,
        }
    )
    if profile_runtime:
        result.update(summarize_runtime_ms(durations))
    if emit_per_sample_csv:
        path = per_sample_csv_path or default_per_sample_csv_path(run_tag)
        frame = build_per_sample_rows(
            test,
            rows,
            subgroup_keys=subgroup_keys,
            extra_fields={
                "algorithm_version": ALGORITHM_VERSION,
                "variant": variant,
                "seed": seed,
                "run_id": run_id,
                "alpha": alpha,
                "alpha_allocation": alpha_allocation,
            },
        )
        write_per_sample_csv(frame, path)
        result["per_sample_csv"] = str(path)
    return result
