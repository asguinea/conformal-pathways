from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from conformal_pathways.conformal.thresholds import allocate_alpha
from conformal_pathways.eval.per_sample_export import make_run_tag
from conformal_pathways.eval.run_with_embeddings import run_evaluation_with_embeddings


def _normalize_alpha_allocations(value):
    modes = (
        [s.strip() for s in value.split(",") if s.strip()]
        if isinstance(value, str)
        else list(value or [])
    )
    modes = list(dict.fromkeys(modes or ["uniform"]))
    for mode in modes:
        allocate_alpha(0.1, 3, mode)
    return modes


def run_single_setting(
    workflow_name, manifest_csv, dataset_root, embeddings_out_path, alpha, seed, variant, **kwargs
):
    return run_evaluation_with_embeddings(
        workflow_name,
        manifest_csv,
        dataset_root,
        embeddings_out_path=embeddings_out_path,
        alpha=alpha,
        seed=seed,
        variant=variant,
        **kwargs,
    )


def run_grid(
    workflow_name,
    manifest_csv,
    dataset_root,
    embeddings_out_path,
    out_csv,
    alphas,
    seeds,
    variants,
    alpha_allocations="",
    per_sample_csv_path=None,
    emit_per_sample_csv=False,
    **kwargs,
):
    modes = _normalize_alpha_allocations(alpha_allocations)
    settings = []
    for alpha, seed, variant, allocation in product(alphas, seeds, variants, modes):
        setting = (
            (None, seed, variant, "uniform")
            if variant == "no_conformal"
            else (alpha, seed, variant, allocation)
        )
        if setting not in settings:
            settings.append(setting)
    if not settings:
        raise ValueError("grid must contain at least one setting")
    rows = []
    for alpha, seed, variant, allocation in settings:
        tag = make_run_tag(workflow_name, alpha, seed, variant, allocation)
        output = None
        if per_sample_csv_path:
            base = Path(per_sample_csv_path)
            output = str(
                base
                if len(settings) == 1
                else base.with_name(f"{base.stem}__{tag}{base.suffix or '.csv'}")
            )
        result = run_single_setting(
            workflow_name,
            manifest_csv,
            dataset_root,
            embeddings_out_path,
            alpha,
            seed,
            variant,
            alpha_allocation=allocation,
            emit_per_sample_csv=emit_per_sample_csv,
            per_sample_csv_path=output,
            **kwargs,
        )
        # Keep all denominators and provenance. Nested records use actual JSON,
        # not Python repr strings; exports can be parsed independently.
        rows.append(
            {
                "workflow_name": workflow_name,
                "dataset": Path(manifest_csv).stem,
                "seed": seed,
                **{
                    k: json.dumps(v, sort_keys=True, allow_nan=False)
                    if isinstance(v, (dict, list))
                    else v
                    for k, v in result.items()
                },
            }
        )
    target = Path(out_csv)
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(target, index=False)


def _parse_csv_list(value: str, cast) -> list[Any]:
    parts = [part.strip() for part in value.split(",")]
    return [cast(part) for part in parts if part]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run grid evaluation with embedding predictor.")
    parser.add_argument(
        "--workflow_name", required=True, choices=["dr_workflow", "glaucoma_workflow"]
    )
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--dataset_root", required=True)
    parser.add_argument("--embeddings_out_path", required=True)
    parser.add_argument("--out_csv", required=True)
    parser.add_argument("--alphas", default="0.1")
    parser.add_argument("--seeds", default="0")
    parser.add_argument("--variants", default="main")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--weights", choices=["IMAGENET1K_V2", "random"], default="IMAGENET1K_V2")
    parser.add_argument("--random_seed", type=int, default=None)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default=None)
    parser.add_argument("--allow_repartition", action="store_true")
    parser.add_argument("--force_extract", action="store_true")
    parser.add_argument("--prefer_mps", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--filter_dme_subset", action=argparse.BooleanOptionalAction, default=False)
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
        weights=args.weights,
        random_seed=args.random_seed,
        device=args.device,
        allow_repartition=args.allow_repartition,
        force_extract=args.force_extract,
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
