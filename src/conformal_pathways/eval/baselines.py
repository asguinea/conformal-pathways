from __future__ import annotations

from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.experiment import evaluate_experiment
from conformal_pathways.eval.runner import (
    make_synthetic_samples_dr,
    make_synthetic_samples_glaucoma,
)
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow


def _workflow_and_predictor(workflow_name: str):
    if workflow_name == "dr_workflow":
        workflow = DRWorkflow()
        predictor = TrivialLabelPredictor(
            label_key="dr_severity",
            class_values=["mild", "moderate", "severe"],
        )
        return workflow, predictor
    if workflow_name == "glaucoma_workflow":
        workflow = GlaucomaWorkflow()
        predictor = TrivialLabelPredictor(
            label_key="glaucoma_risk",
            class_values=["low", "high"],
        )
        return workflow, predictor
    raise ValueError(
        f"Unsupported workflow_name '{workflow_name}'. "
        "Expected 'dr_workflow' or 'glaucoma_workflow'."
    )


def _weights_for_variant(variant: str) -> tuple[float, float]:
    if variant == "main":
        return 1.0, 1.0
    if variant == "rules_only":
        return 0.0, 1.0
    if variant == "model_only":
        return 1.0, 0.0
    if variant == "no_conformal":
        return 1.0, 1.0
    raise ValueError(
        f"Unsupported variant '{variant}'. "
        "Expected one of: main, rules_only, model_only, no_conformal."
    )


def run_method_variant(workflow_name, samples, splits, alpha, variant):
    workflow, predictor = _workflow_and_predictor(workflow_name)
    return evaluate_experiment(workflow, samples, splits, predictor, alpha=alpha, variant=variant)


def run_synthetic_comparison(
    workflow_name: str,
    n: int,
    seed: int,
    alpha: float,
) -> dict[str, dict[str, float]]:
    if workflow_name == "dr_workflow":
        samples = make_synthetic_samples_dr(n=n, seed=seed)
    elif workflow_name == "glaucoma_workflow":
        samples = make_synthetic_samples_glaucoma(n=n, seed=seed)
    else:
        raise ValueError(
            f"Unsupported workflow_name '{workflow_name}'. "
            "Expected 'dr_workflow' or 'glaucoma_workflow'."
        )

    splits = make_splits(
        samples=samples,
        seed=seed,
        ratios=(0.6, 0.2, 0.2),
        stratify_by_source=False,
    )

    variants = ["main", "rules_only", "model_only", "no_conformal"]
    return {
        variant: run_method_variant(
            workflow_name=workflow_name,
            samples=samples,
            splits=splits,
            alpha=alpha,
            variant=variant,
        )
        for variant in variants
    }
