from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from conformal_pathways.conformal import (
    build_prediction_set,
    collect_oracle_scores_by_stage,
    compute_stage_thresholds,
)
from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.case_traces import export_case_trace, parse_case_trace_ids
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
from conformal_pathways.eval.run_with_embeddings import (
    _ids_path_for,
    _infer_dr_classes,
    _infer_glaucoma_classes,
    _normalize_embeddings_out_path,
    samples_from_manifest_csv,
)
from conformal_pathways.features.extract_embeddings import extract_embeddings_from_manifest
from conformal_pathways.models.embedding_predictor import EmbeddingLogRegPredictor
from conformal_pathways.workflows.dr import DRWorkflow
from conformal_pathways.workflows.glaucoma import GlaucomaWorkflow


def _normalize_alpha_allocations(alpha_allocations: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if alpha_allocations is None:
        return ["uniform"]
    if isinstance(alpha_allocations, str):
        items = [item.strip() for item in alpha_allocations.split(",")]
        parsed = [item for item in items if item]
        return parsed or ["uniform"]
    parsed = [str(item).strip() for item in alpha_allocations if str(item).strip()]
    return parsed or ["uniform"]


def _weights_for_variant(variant: str) -> tuple[float, float]:
    if variant == "main":
        return 1.0, 1.0
    if variant == "rules_only":
        return 0.0, 1.0
    if variant == "uncertainty_only":
        return 1.0, 0.0
    if variant == "no_conformal":
        return 1.0, 1.0
    raise ValueError(f"unsupported variant '{variant}'")


def run_single_setting(
    workflow_name: str,
    manifest_csv: str,
    dataset_root: str,
    embeddings_out_path: str,
    alpha: float | None,
    seed: int,
    variant: str,
    alpha_allocation: str = "uniform",
    batch_size: int = 32,
    prefer_mps: bool = True,
    filter_dme_subset: bool = True,
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
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
    if workflow_name == "dr_workflow":
        workflow = DRWorkflow()
        label_key = "dr_severity"
    elif workflow_name == "glaucoma_workflow":
        workflow = GlaucomaWorkflow()
        label_key = "glaucoma_risk"
    else:
        raise ValueError(
            f"Unsupported workflow_name '{workflow_name}'. "
            "Expected 'dr_workflow' or 'glaucoma_workflow'."
        )

    samples = samples_from_manifest_csv(manifest_csv)
    if workflow_name == "dr_workflow" and filter_dme_subset:
        samples = [sample for sample in samples if sample.dme_label_available()]
    if not samples:
        raise ValueError("no samples available after filtering")

    subset_df = pd.DataFrame(
        {
            "sample_id": [sample.sample_id for sample in samples],
            "image_path": [sample.image_path for sample in samples],
            "dataset_source": [sample.dataset_source for sample in samples],
        }
    )
    subset_manifest_path = Path(embeddings_out_path).with_suffix(".subset_manifest.csv")
    subset_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    subset_df.to_csv(subset_manifest_path, index=False)

    normalized_out_path = _normalize_embeddings_out_path(embeddings_out_path)
    ids_path_obj = _ids_path_for(normalized_out_path)
    if normalized_out_path.exists() and ids_path_obj.exists():
        print(f"Using cached embeddings at {embeddings_out_path}")
        embeddings_path = str(normalized_out_path)
        ids_path = str(ids_path_obj)
    else:
        stats = extract_embeddings_from_manifest(
            manifest_csv=str(subset_manifest_path),
            dataset_root=dataset_root,
            out_path=embeddings_out_path,
            batch_size=batch_size,
            prefer_mps=prefer_mps,
            max_items=None,
        )
        embeddings_path = str(stats["out_path"])
        ids_path = str(_ids_path_for(Path(embeddings_path)))

    splits = make_splits(
        samples=samples,
        seed=seed,
        ratios=ratios,
        stratify_by_source=True,
    )
    sample_by_id = {sample.sample_id: sample for sample in samples}
    train_samples = [sample_by_id[sample_id] for sample_id in splits["train"]]
    cal_samples = [sample_by_id[sample_id] for sample_id in splits["cal"]]
    test_samples = [sample_by_id[sample_id] for sample_id in splits["test"]]

    if not train_samples or not cal_samples or not test_samples:
        raise ValueError("insufficient split sizes for train/cal/test")

    if workflow_name == "dr_workflow":
        class_values = _infer_dr_classes(train_samples)
    else:
        class_values = _infer_glaucoma_classes(train_samples)

    label_map = {
        sample.sample_id: sample.get_label(label_key)
        for sample in samples
        if sample.has_label(label_key)
    }
    predictor = EmbeddingLogRegPredictor(
        embeddings_path=embeddings_path,
        ids_path=ids_path,
        label_map=label_map,
        class_values=class_values,
    )
    predictor.fit(train_samples)

    w_u, w_r = _weights_for_variant(variant)
    scores_by_stage = collect_oracle_scores_by_stage(
        workflow=workflow,
        samples=cal_samples,
        predictor=predictor,
        workflow_name=workflow.name,
        w_u=w_u,
        w_r=w_r,
    )

    if variant == "no_conformal":
        thresholds = {}
        for stage, stage_scores in scores_by_stage.items():
            if not stage_scores:
                raise ValueError(f"no calibration scores at stage {stage}")
            thresholds[stage] = max(stage_scores)
    else:
        if alpha is None:
            raise ValueError("alpha must be provided for conformal variants")
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
            w_u=w_u,
            w_r=w_r,
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
            dataset_token = Path(manifest_csv).stem
            alpha_token = alpha if alpha is not None else "none"
            run_tag = make_run_tag(
                workflow.name,
                dataset_token,
                f"alpha_{alpha_token}",
                f"allocation_{alpha_allocation}",
                f"seed_{seed}",
                f"variant_{variant}",
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
                alpha=float(alpha) if alpha is not None else 0.0,
                alpha_allocation=alpha_allocation,
                stage_thresholds=thresholds,
                selection_policies=policy_names,
                pi=prediction_set,
                extra_context={
                    "dataset": dataset_token,
                    "variant": variant,
                    "seed": seed,
                    "subgroups": subgroup_values,
                },
            )
            exported_case_ids.add(sample_id)

    metrics = aggregate_metrics(metrics_list)
    if policy_names:
        metrics.update(aggregate_chosen_path_metrics(chosen_metrics_list))
        metrics.update(
            aggregate_topk_safety_metrics(
                topk_metrics_list,
                ranking_policies=policy_names,
                ks=(2, 3),
            )
        )
    if profile_runtime:
        metrics.update(summarize_runtime_ms(runtime_ms_per_sample))
    metrics.update(
        {
            "alpha_allocation": alpha_allocation,
            "n_total": float(len(samples)),
            "n_train": float(len(train_samples)),
            "n_cal": float(len(cal_samples)),
            "n_test": float(len(test_samples)),
        }
    )
    if emit_per_sample_csv:
        dataset_token = Path(manifest_csv).stem
        alpha_token = alpha if alpha is not None else "none"
        run_tag = make_run_tag(
            workflow.name,
            dataset_token,
            f"alpha_{alpha_token}",
            f"allocation_{alpha_allocation}",
            f"seed_{seed}",
            f"variant_{variant}",
        )
        out_path = per_sample_csv_path or default_per_sample_csv_path(run_tag)
        per_sample_df = build_per_sample_rows(
            samples=processed_test_samples if processed_test_samples else test_samples,
            per_sample_metrics=per_sample_metric_rows,
            subgroup_keys=subgroup_cols,
            extra_fields={
                "workflow_name": workflow.name,
                "dataset": dataset_token,
                "alpha": alpha,
                "alpha_allocation": alpha_allocation,
                "seed": seed,
                "variant": variant,
            },
        )
        write_per_sample_csv(per_sample_df, out_path)
    return metrics


def run_grid(
    workflow_name: str,
    manifest_csv: str,
    dataset_root: str,
    embeddings_out_path: str,
    out_csv: str,
    alphas: list[float],
    seeds: list[int],
    variants: list[str],
    batch_size: int = 32,
    prefer_mps: bool = True,
    filter_dme_subset: bool = True,
    alpha_allocations: str | list[str] = "",
    selection_policies: str | list[str] = "",
    debug_print_selected_paths: bool = False,
    emit_per_sample_csv: bool = False,
    per_sample_csv_path: str | None = None,
    subgroup_keys: str = "",
    profile_runtime: bool = False,
    export_case_traces: str = "",
    case_trace_out_dir: str = "artifacts/qualitative",
    case_trace_subgroup_keys: str = "",
) -> None:
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dataset_name = Path(manifest_csv).stem
    allocation_modes = _normalize_alpha_allocations(alpha_allocations)
    total_settings = len(alphas) * len(seeds) * len(variants) * len(allocation_modes)
    rows: list[dict[str, Any]] = []
    for alpha in alphas:
        for seed in seeds:
            for variant in variants:
                for alpha_allocation in allocation_modes:
                    setting_alpha: float | None = alpha
                    if variant == "no_conformal":
                        setting_alpha = None

                    setting_per_sample_csv_path: str | None = None
                    if emit_per_sample_csv:
                        if per_sample_csv_path is None:
                            setting_per_sample_csv_path = None
                        elif total_settings == 1:
                            setting_per_sample_csv_path = per_sample_csv_path
                        else:
                            base_path = Path(per_sample_csv_path)
                            alpha_token = setting_alpha if setting_alpha is not None else "none"
                            run_tag = make_run_tag(
                                workflow_name,
                                dataset_name,
                                f"alpha_{alpha_token}",
                                f"allocation_{alpha_allocation}",
                                f"seed_{seed}",
                                f"variant_{variant}",
                            )
                            suffix = base_path.suffix or ".csv"
                            stem = base_path.stem if base_path.suffix else base_path.name
                            setting_per_sample_csv_path = str(
                                base_path.with_name(f"{stem}__{run_tag}{suffix}")
                            )

                    metrics = run_single_setting(
                        workflow_name=workflow_name,
                        manifest_csv=manifest_csv,
                        dataset_root=dataset_root,
                        embeddings_out_path=embeddings_out_path,
                        alpha=setting_alpha,
                        alpha_allocation=alpha_allocation,
                        seed=seed,
                        variant=variant,
                        batch_size=batch_size,
                        prefer_mps=prefer_mps,
                        filter_dme_subset=filter_dme_subset,
                        selection_policies=selection_policies,
                        debug_print_selected_paths=debug_print_selected_paths,
                        emit_per_sample_csv=emit_per_sample_csv,
                        per_sample_csv_path=setting_per_sample_csv_path,
                        subgroup_keys=subgroup_keys,
                        profile_runtime=profile_runtime,
                        export_case_traces=export_case_traces,
                        case_trace_out_dir=case_trace_out_dir,
                        case_trace_subgroup_keys=case_trace_subgroup_keys,
                    )
                    row = {
                        "workflow_name": workflow_name,
                        "dataset": dataset_name,
                        "alpha": alpha if setting_alpha is not None else None,
                        "alpha_allocation": alpha_allocation,
                        "seed": seed,
                        "variant": variant,
                        "existential_safe": metrics["existential_safe"],
                        "oracle_retained": metrics["oracle_retained"],
                        "set_size": metrics["set_size"],
                        "empty_set_rate": metrics["empty_set_rate"],
                        "unsafe_exposure": metrics["unsafe_exposure"],
                        "n_total": metrics["n_total"],
                        "n_train": metrics["n_train"],
                        "n_cal": metrics["n_cal"],
                        "n_test": metrics["n_test"],
                    }
                    for key, value in metrics.items():
                        if (
                            key.startswith("chosen_")
                            or key.startswith("top")
                            or key.startswith("runtime_")
                        ):
                            row[key] = value
                    rows.append(row)

    pd.DataFrame(rows).to_csv(out_path, index=False)


def _parse_csv_list(value: str, cast) -> list[Any]:
    parts = [part.strip() for part in value.split(",")]
    return [cast(part) for part in parts if part]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run grid evaluation with embedding predictor.")
    parser.add_argument("--workflow_name", required=True, choices=["dr_workflow", "glaucoma_workflow"])
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--dataset_root", required=True)
    parser.add_argument("--embeddings_out_path", required=True)
    parser.add_argument("--out_csv", required=True)
    parser.add_argument("--alphas", default="0.1")
    parser.add_argument("--seeds", default="0")
    parser.add_argument("--variants", default="main")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--prefer_mps", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--filter_dme_subset", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--alpha_allocations", default="")
    parser.add_argument("--selection_policies", default="")
    parser.add_argument("--debug_print_selected_paths", action="store_true")
    parser.add_argument("--emit_per_sample_csv", action="store_true")
    parser.add_argument("--per_sample_csv_path", default=None)
    parser.add_argument("--subgroup_keys", default="")
    parser.add_argument("--profile_runtime", action="store_true")
    parser.add_argument("--export_case_traces", default="")
    parser.add_argument("--case_trace_out_dir", default="artifacts/qualitative")
    parser.add_argument("--case_trace_subgroup_keys", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    run_grid(
        workflow_name=args.workflow_name,
        manifest_csv=args.manifest_csv,
        dataset_root=args.dataset_root,
        embeddings_out_path=args.embeddings_out_path,
        out_csv=args.out_csv,
        alphas=_parse_csv_list(args.alphas, float),
        seeds=_parse_csv_list(args.seeds, int),
        variants=_parse_csv_list(args.variants, str),
        batch_size=args.batch_size,
        prefer_mps=args.prefer_mps,
        filter_dme_subset=args.filter_dme_subset,
        alpha_allocations=args.alpha_allocations,
        selection_policies=args.selection_policies,
        debug_print_selected_paths=args.debug_print_selected_paths,
        emit_per_sample_csv=args.emit_per_sample_csv,
        per_sample_csv_path=args.per_sample_csv_path,
        subgroup_keys=args.subgroup_keys,
        profile_runtime=args.profile_runtime,
        export_case_traces=args.export_case_traces,
        case_trace_out_dir=args.case_trace_out_dir,
        case_trace_subgroup_keys=args.case_trace_subgroup_keys,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
