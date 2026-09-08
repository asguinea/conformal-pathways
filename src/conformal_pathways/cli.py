"""Small, offline entry point for checking the experimental pipeline."""

from __future__ import annotations

import argparse
import json
import math

from conformal_pathways import __version__


def _sample_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("n must be an integer") from exc
    if count < 20:
        raise argparse.ArgumentTypeError("n must be at least 20 to populate all demo splits")
    return count


def _alpha(value: str) -> float:
    try:
        alpha = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("alpha must be a number") from exc
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise argparse.ArgumentTypeError("alpha must be finite and strictly between 0 and 1")
    return alpha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Conformal Pathways: experimental decision-workflow tooling."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run an offline synthetic installation check")
    demo.add_argument("--workflow", choices=("dr", "glaucoma"), default="dr")
    demo.add_argument("--n", type=_sample_count, default=100)
    demo.add_argument("--seed", type=int, default=0)
    demo.add_argument("--alpha", type=_alpha, default=0.1)
    args = parser.parse_args(argv)

    # Keep help and version independent of scientific or optional imports.
    from conformal_pathways.eval.runner import run_synthetic_experiment

    metrics = run_synthetic_experiment(
        workflow_name=f"{args.workflow}_workflow",
        n=args.n,
        seed=args.seed,
        alpha=args.alpha,
        alpha_allocation="uniform",
    )
    payload = {
        "schema_version": 2,
        "project_version": __version__,
        "verification_scope": "installation_smoke_only",
        "scientific_validation": "see_claim_register",
        "notice": (
            "Synthetic class-prior demonstration of the entry-observation toy protocol. "
            "These values do not establish predictive performance or clinical safety."
        ),
        "config": {
            "workflow": args.workflow,
            "n": args.n,
            "seed": args.seed,
            "alpha": args.alpha,
            "alpha_allocation": "uniform",
        },
        "experimental_metrics": metrics,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return 0
