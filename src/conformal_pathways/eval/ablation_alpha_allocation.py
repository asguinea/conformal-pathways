from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from conformal_pathways.eval.grid_runner import run_grid


def _parse_csv_list(value: str, cast) -> list:
    parts = [part.strip() for part in value.split(",")]
    return [cast(part) for part in parts if part]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Alpha-allocation ablation runner.")
    parser.add_argument(
        "--workflow_name", required=True, choices=["dr_workflow", "glaucoma_workflow"]
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset_root", required=True)
    parser.add_argument("--embeddings_out_path", required=True)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--variant", default="main")
    parser.add_argument("--selection_policies", default="")
    parser.add_argument("--out_csv", required=True)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--prefer_mps", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--filter_dme_subset", action=argparse.BooleanOptionalAction, default=False)
    return parser


def run_ablation(
    workflow_name: str,
    manifest_csv: str,
    dataset_root: str,
    embeddings_out_path: str,
    alpha: float,
    seeds: list[int],
    variant: str,
    selection_policies: str,
    out_csv: str,
    batch_size: int = 32,
    prefer_mps: bool = True,
    filter_dme_subset: bool = False,
) -> str:
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw_out = out_path.with_name(f"{out_path.stem}__raw.csv")

    run_grid(
        workflow_name=workflow_name,
        manifest_csv=manifest_csv,
        dataset_root=dataset_root,
        embeddings_out_path=embeddings_out_path,
        out_csv=str(raw_out),
        alphas=[alpha],
        seeds=seeds,
        variants=[variant],
        batch_size=batch_size,
        prefer_mps=prefer_mps,
        filter_dme_subset=filter_dme_subset,
        alpha_allocations="uniform,front_loaded,back_loaded",
        selection_policies=selection_policies,
    )

    df = pd.read_csv(raw_out)
    metric_cols = [
        "existential_safe",
        "unsafe_exposure",
        "set_size",
        "empty_set_rate",
        "chosen_unsafe_rate__observed_rules_first",
        "top2_has_safe_rate__observed_rules_first",
        "chosen_unsafe_rate__min_total_score",
        "top2_has_safe_rate__min_total_score",
    ]
    present_metric_cols = [col for col in metric_cols if col in df.columns]

    records = []
    for allocation, group in df.groupby("alpha_allocation", sort=True):
        record = {
            "alpha_allocation": allocation,
            "summary_kind": "unweighted_mean_of_run_metrics",
            "n_runs": len(group),
            "raw_results_csv": str(raw_out),
        }
        for column in present_metric_cols:
            values = pd.to_numeric(group[column], errors="raise").dropna()
            record[column] = float(values.mean()) if len(values) else None
            record[column + "__numerator"] = float(values.sum())
            record[column + "__denominator"] = len(values)
            record[column + "__unavailable"] = len(group) - len(values)
        records.append(record)
    agg = pd.DataFrame(records)
    agg.to_csv(out_path, index=False)
    return str(out_path)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    out_path = run_ablation(
        workflow_name=args.workflow_name,
        manifest_csv=args.manifest,
        dataset_root=args.dataset_root,
        embeddings_out_path=args.embeddings_out_path,
        alpha=args.alpha,
        seeds=_parse_csv_list(args.seeds, int),
        variant=args.variant,
        selection_policies=args.selection_policies,
        out_csv=args.out_csv,
        batch_size=args.batch_size,
        prefer_mps=args.prefer_mps,
        filter_dme_subset=args.filter_dme_subset,
    )
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
