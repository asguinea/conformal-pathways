from __future__ import annotations

import argparse
import random

from conformal_pathways.data import Sample
from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.experiment import evaluate_experiment
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow


def make_synthetic_samples_dr(n: int, seed: int) -> list[Sample]:
    rng = random.Random(seed)
    severities = ["mild", "moderate", "severe"]
    samples: list[Sample] = []

    for i in range(n):
        patient_index = i // 2
        dataset_source = "A" if patient_index % 2 == 0 else "B"
        sample = Sample(
            sample_id=f"dr_{i}",
            dataset_source=dataset_source,
            image_path=None,
            labels={
                "dr_severity": rng.choice(severities),
                "dme_positive": rng.choice([False, True]),
            },
            meta={"patient_id": f"dr_patient_{patient_index}"},
        )
        samples.append(sample)

    return samples


def make_synthetic_samples_glaucoma(n: int, seed: int) -> list[Sample]:
    rng = random.Random(seed)
    risks = ["low", "high"]
    samples: list[Sample] = []

    for i in range(n):
        patient_index = i // 2
        dataset_source = "A" if patient_index % 2 == 0 else "B"
        sample = Sample(
            sample_id=f"glaucoma_{i}",
            dataset_source=dataset_source,
            image_path=None,
            labels={"glaucoma_risk": rng.choice(risks)},
            meta={"patient_id": f"glaucoma_patient_{patient_index}"},
        )
        samples.append(sample)

    return samples


def run_synthetic_experiment(
    workflow_name, n=40, seed=0, alpha=0.1, alpha_allocation="uniform", **kwargs
):
    if n < 20:
        raise ValueError("synthetic experiment needs at least 20 samples")
    if workflow_name == "dr_workflow":
        workflow, samples = DRWorkflow(), make_synthetic_samples_dr(n, seed)
        predictor = TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"])
    elif workflow_name == "glaucoma_workflow":
        workflow, samples = GlaucomaWorkflow(), make_synthetic_samples_glaucoma(n, seed)
        predictor = TrivialLabelPredictor("glaucoma_risk", ["low", "high"])
    else:
        raise ValueError("unsupported workflow")
    splits = make_splits(samples, seed)
    return evaluate_experiment(
        workflow,
        samples,
        splits,
        predictor,
        alpha=alpha,
        alpha_allocation=alpha_allocation,
        seed=seed,
        **kwargs,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run synthetic workflow evaluation.")
    parser.add_argument(
        "--workflow_name",
        choices=["all", "dr_workflow", "glaucoma_workflow"],
        default="all",
    )
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--alpha_allocation", default="uniform")
    parser.add_argument("--debug_eval_introspection", action="store_true")
    parser.add_argument("--debug_eval_introspection_exit", action="store_true")
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

    workflow_names = (
        ("dr_workflow", "glaucoma_workflow")
        if args.workflow_name == "all"
        else (args.workflow_name,)
    )
    for workflow_name in workflow_names:
        result = run_synthetic_experiment(
            workflow_name=workflow_name,
            n=args.n,
            seed=args.seed,
            alpha=args.alpha,
            alpha_allocation=args.alpha_allocation,
            debug_eval_introspection=args.debug_eval_introspection,
            debug_eval_introspection_exit=args.debug_eval_introspection_exit,
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
        print(f"{workflow_name}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
