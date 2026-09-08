from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from conformal_pathways.conformal import (
    build_prediction_set,
    collect_oracle_scores_by_stage,
    compute_stage_thresholds,
)
from conformal_pathways.data.loaders import filter_dme_labeled, load_samples_from_csv
from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.case_traces import export_case_trace, parse_case_trace_ids
from conformal_pathways.eval.introspection import describe_prediction_set
from conformal_pathways.eval.metrics import (
    aggregate_chosen_path_metrics,
    aggregate_metrics,
    aggregate_topk_safety_metrics,
    compute_chosen_path_metrics,
    compute_sample_metrics,
    compute_topk_safety_metrics,
)
from conformal_pathways.eval.per_sample_export import (
    build_per_sample_rows,
    default_per_sample_csv_path,
    make_run_tag,
    parse_subgroup_keys,
    write_per_sample_csv,
)
from conformal_pathways.eval.runtime import summarize_runtime_ms
from conformal_pathways.eval.selection_policies import (
    normalize_selection_policies,
    render_pathway,
    select_pathway,
)
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows.dr import DRWorkflow
from conformal_pathways.workflows.glaucoma import GlaucomaWorkflow


def _infer_class_values(
    train_samples: list,
    label_key: str,
    canonical: list[Any],
) -> list[Any]:
    observed = {
        sample.get_label(label_key)
        for sample in train_samples
        if sample.has_label(label_key)
    }
    observed = {value for value in observed if value is not None}

    if observed and observed.issubset(set(canonical)):
        return list(canonical)
    if observed:
        return sorted(observed, key=lambda value: (str(type(value)), str(value)))
    return list(canonical)


def run_evaluation_from_csv(
    workflow_name: str,
    csv_path: str,
    dataset_source: str,
    label_cols: list[str],
    meta_cols: list[str],
    seed: int = 0,
    alpha: float = 0.1,
    alpha_allocation: str = "uniform",
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    filter_dme_subset: bool = True,
    debug_eval_introspection: bool = False,
    debug_eval_introspection_exit: bool = False,
    selection_policies: str | list[str] = "",
    debug_print_selected_paths: bool = False,
    emit_per_sample_csv: bool = False,
    per_sample_csv_path: str | None = None,
    subgroup_keys: str = "",
    profile_runtime: bool = False,
    export_case_traces: str = "",
    case_trace_out_dir: str = "artifacts/qualitative",
    case_trace_subgroup_keys: str = "",
) -> dict[str, Any]:
    samples = load_samples_from_csv(
        csv_path=csv_path,
        dataset_source=dataset_source,
        label_cols=label_cols,
        meta_cols=meta_cols,
    )

    if workflow_name == "dr_workflow":
        workflow = DRWorkflow()
        if filter_dme_subset:
            samples = filter_dme_labeled(samples)
        predictor_label_key = "dr_severity"
        canonical_classes = ["mild", "moderate", "severe"]
    elif workflow_name == "glaucoma_workflow":
        workflow = GlaucomaWorkflow()
        predictor_label_key = "glaucoma_risk"
        canonical_classes = ["low", "high"]
    else:
        raise ValueError(
            f"Unsupported workflow_name '{workflow_name}'. "
            "Expected 'dr_workflow' or 'glaucoma_workflow'."
        )

    if not samples:
        raise ValueError("No samples available after loading/filtering")

    splits = make_splits(
        samples=samples,
        seed=seed,
        ratios=ratios,
        stratify_by_source=True,
    )
    samples_by_id = {sample.sample_id: sample for sample in samples}
    train_samples = [samples_by_id[sample_id] for sample_id in splits["train"]]
    cal_samples = [samples_by_id[sample_id] for sample_id in splits["cal"]]
    test_samples = [samples_by_id[sample_id] for sample_id in splits["test"]]

    if not train_samples or not cal_samples or not test_samples:
        raise ValueError(
            "Insufficient split sizes; ensure dataset has enough grouped samples for train/cal/test"
        )

    class_values = _infer_class_values(train_samples, predictor_label_key, canonical_classes)
    predictor = TrivialLabelPredictor(
        label_key=predictor_label_key,
        class_values=class_values,
    )
    predictor.fit(train_samples)

    scores_by_stage = collect_oracle_scores_by_stage(
        workflow=workflow,
        samples=cal_samples,
        predictor=predictor,
        workflow_name=workflow.name,
    )
    thresholds = compute_stage_thresholds(
        scores_by_stage=scores_by_stage,
        alpha=alpha,
        mode=alpha_allocation,
    )

    metrics_list: list[dict[str, float | int | bool]] = []
    chosen_metrics_list: list[dict[str, bool]] = []
    topk_metrics_list: list[dict[str, bool]] = []
    runtime_ms_per_sample: list[float] = []
    per_sample_metric_rows: list[dict[str, Any]] = []
    processed_test_samples: list[Any] = []
    policy_names = normalize_selection_policies(selection_policies)
    subgroup_cols = parse_subgroup_keys(subgroup_keys)
    case_trace_ids = parse_case_trace_ids(export_case_traces)
    case_trace_subgroups = parse_subgroup_keys(case_trace_subgroup_keys)
    exported_case_ids: set[str] = set()
    selection_preview_limit = min(5, len(test_samples)) if policy_names else 0
    debug_preview_limit = min(5, len(test_samples)) if debug_eval_introspection else 0
    for sample_idx, sample in enumerate(test_samples):
        # Runtime profile measures per-sample conformal prediction-set build + metric evaluation only.
        if profile_runtime:
            sample_t0 = perf_counter()
        prediction_set = build_prediction_set(
            workflow=workflow,
            sample=sample,
            predictor=predictor,
            workflow_name=workflow.name,
            thresholds=thresholds,
        )
        sample_metric = compute_sample_metrics(
            workflow=workflow,
            workflow_name=workflow.name,
            sample=sample,
            prediction_set=prediction_set,
        )
        chosen_for_sample: dict[str, bool] = {}
        topk_for_sample: dict[str, bool] = {}
        if policy_names:
            chosen_for_sample = compute_chosen_path_metrics(
                prediction_set=prediction_set,
                workflow=workflow,
                workflow_name=workflow.name,
                sample=sample,
                predictor=predictor,
                selection_policies=policy_names,
            )
            topk_for_sample = compute_topk_safety_metrics(
                prediction_set=prediction_set,
                workflow=workflow,
                workflow_name=workflow.name,
                sample=sample,
                predictor=predictor,
                ranking_policies=policy_names,
                ks=(2, 3),
            )
        if profile_runtime:
            runtime_ms = (perf_counter() - sample_t0) * 1000.0
            runtime_ms_per_sample.append(runtime_ms)
        if sample_idx < selection_preview_limit:
            for policy_name in policy_names:
                try:
                    selected = select_pathway(
                        pi=prediction_set,
                        workflow=workflow,
                        sample=sample,
                        predictor=predictor,
                        policy=policy_name,
                    )
                    print(f"[{policy_name}] selected: {render_pathway(selected)}")
                    if debug_print_selected_paths:
                        print(
                            f"[{policy_name}] sample_id={sample.sample_id} "
                            f"retained={len(prediction_set)}"
                        )
                except Exception as exc:  # pragma: no cover - defensive
                    print(
                        f"[{policy_name}] selection failed for "
                        f"sample_id={sample.sample_id}: {exc}"
                    )
        if debug_eval_introspection and sample_idx < debug_preview_limit:
            try:
                print(
                    describe_prediction_set(
                        pi=prediction_set,
                        workflow=workflow,
                        sample=sample,
                        extra_context={
                            "workflow_name": workflow.name,
                            "sample_index": sample_idx,
                            "n_test": len(test_samples),
                            "thresholds": thresholds,
                        },
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive
                print(
                    "[debug_eval_introspection] failed for "
                    f"sample_id={sample.sample_id}: {exc}"
                )
        metrics_list.append(sample_metric)
        if policy_names:
            chosen_metrics_list.append(chosen_for_sample)
            topk_metrics_list.append(topk_for_sample)
        if emit_per_sample_csv:
            row = dict(sample_metric)
            row.update(chosen_for_sample)
            row.update(topk_for_sample)
            if profile_runtime:
                row["runtime_ms"] = runtime_ms_per_sample[-1]
            per_sample_metric_rows.append(row)
            processed_test_samples.append(sample)
        sample_id = str(getattr(sample, "sample_id", ""))
        if sample_id in case_trace_ids and sample_id not in exported_case_ids:
            run_tag = make_run_tag(
                workflow.name,
                dataset_source,
                f"alpha_{alpha}",
                f"allocation_{alpha_allocation}",
                f"seed_{seed}",
                "variant_main",
            )
            subgroup_values = {
                key: getattr(sample, "meta", {}).get(key, getattr(sample, "labels", {}).get(key))
                for key in case_trace_subgroups
            }
            trace_path = Path(case_trace_out_dir) / f"{run_tag}__sample_{sample_id}.json"
            export_case_trace(
                out_path=str(trace_path),
                workflow=workflow,
                sample=sample,
                predictor=predictor,
                alpha=alpha,
                alpha_allocation=alpha_allocation,
                stage_thresholds=thresholds,
                selection_policies=policy_names,
                pi=prediction_set,
                extra_context={
                    "dataset": dataset_source,
                    "variant": "main",
                    "seed": seed,
                    "subgroups": subgroup_values,
                },
            )
            exported_case_ids.add(sample_id)
        if (
            debug_eval_introspection
            and debug_eval_introspection_exit
            and sample_idx + 1 >= debug_preview_limit
        ):
            print("[debug_eval_introspection] exiting early after preview subset.")
            result = aggregate_metrics(metrics_list)
            result["alpha_allocation"] = alpha_allocation
            if policy_names:
                result.update(aggregate_chosen_path_metrics(chosen_metrics_list))
                result.update(
                    aggregate_topk_safety_metrics(
                        topk_metrics_list,
                        ranking_policies=policy_names,
                        ks=(2, 3),
                    )
                )
            if profile_runtime:
                result.update(summarize_runtime_ms(runtime_ms_per_sample))
            if emit_per_sample_csv:
                run_tag = make_run_tag(
                    workflow.name,
                    dataset_source,
                    f"alpha_{alpha}",
                    f"allocation_{alpha_allocation}",
                    f"seed_{seed}",
                    "variant_main",
                )
                out_path = per_sample_csv_path or default_per_sample_csv_path(run_tag)
                per_sample_df = build_per_sample_rows(
                    samples=processed_test_samples,
                    per_sample_metrics=per_sample_metric_rows,
                    subgroup_keys=subgroup_cols,
                    extra_fields={
                        "workflow_name": workflow.name,
                        "dataset": dataset_source,
                        "alpha": alpha,
                        "alpha_allocation": alpha_allocation,
                        "seed": seed,
                        "variant": "main",
                    },
                )
                write_per_sample_csv(per_sample_df, out_path)
            return result

    result = aggregate_metrics(metrics_list)
    result["alpha_allocation"] = alpha_allocation
    if policy_names:
        result.update(aggregate_chosen_path_metrics(chosen_metrics_list))
        result.update(
            aggregate_topk_safety_metrics(
                topk_metrics_list,
                ranking_policies=policy_names,
                ks=(2, 3),
            )
        )
    if profile_runtime:
        result.update(summarize_runtime_ms(runtime_ms_per_sample))
    if emit_per_sample_csv:
        run_tag = make_run_tag(
            workflow.name,
            dataset_source,
            f"alpha_{alpha}",
            f"allocation_{alpha_allocation}",
            f"seed_{seed}",
            "variant_main",
        )
        out_path = per_sample_csv_path or default_per_sample_csv_path(run_tag)
        per_sample_df = build_per_sample_rows(
            samples=processed_test_samples if processed_test_samples else test_samples,
            per_sample_metrics=per_sample_metric_rows,
            subgroup_keys=subgroup_cols,
            extra_fields={
                "workflow_name": workflow.name,
                "dataset": dataset_source,
                "alpha": alpha,
                "alpha_allocation": alpha_allocation,
                "seed": seed,
                "variant": "main",
            },
        )
        write_per_sample_csv(per_sample_df, out_path)
    return result
