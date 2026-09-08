from __future__ import annotations

from conformal_pathways.conformal import (
    build_prediction_set,
    collect_oracle_scores_by_stage,
    compute_stage_thresholds,
)
from conformal_pathways.data import Sample
from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.metrics import aggregate_metrics, compute_sample_metrics
from conformal_pathways.eval.runner import make_synthetic_samples_dr, make_synthetic_samples_glaucoma
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows.dr import DRWorkflow
from conformal_pathways.workflows.glaucoma import GlaucomaWorkflow


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
    if variant == "uncertainty_only":
        return 1.0, 0.0
    if variant == "no_conformal":
        return 1.0, 1.0
    raise ValueError(
        f"Unsupported variant '{variant}'. "
        "Expected one of: main, rules_only, uncertainty_only, no_conformal."
    )


def run_method_variant(
    workflow_name: str,
    samples: list[Sample],
    splits: dict[str, list[str]],
    alpha: float,
    variant: str,
) -> dict[str, float]:
    workflow, predictor = _workflow_and_predictor(workflow_name)
    w_u, w_r = _weights_for_variant(variant)

    sample_by_id = {sample.sample_id: sample for sample in samples}
    train_samples = [sample_by_id[sample_id] for sample_id in splits["train"]]
    cal_samples = [sample_by_id[sample_id] for sample_id in splits["cal"]]
    test_samples = [sample_by_id[sample_id] for sample_id in splits["test"]]

    predictor.fit(train_samples)
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
                raise ValueError(f"calibration scores are empty at stage {stage}")
            thresholds[stage] = max(stage_scores)
    else:
        thresholds = compute_stage_thresholds(
            scores_by_stage=scores_by_stage,
            alpha=alpha,
            mode="uniform",
        )

    metrics_per_sample: list[dict[str, float | int | bool]] = []
    for sample in test_samples:
        prediction_set = build_prediction_set(
            workflow=workflow,
            sample=sample,
            predictor=predictor,
            workflow_name=workflow.name,
            thresholds=thresholds,
            w_u=w_u,
            w_r=w_r,
        )
        metrics_per_sample.append(
            compute_sample_metrics(
                workflow=workflow,
                workflow_name=workflow.name,
                sample=sample,
                prediction_set=prediction_set,
            )
        )

    return aggregate_metrics(metrics_per_sample)


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
        stratify_by_source=True,
    )

    variants = ["main", "rules_only", "uncertainty_only", "no_conformal"]
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
