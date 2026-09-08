from __future__ import annotations

from conformal_pathways.data.loaders import load_samples_from_csv
from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.experiment import evaluate_experiment
from conformal_pathways.models import TrivialLabelPredictor
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow


def _infer_class_values(train_samples, label_key, canonical):
    observed = {s.get_label(label_key) for s in train_samples if s.has_label(label_key)}
    if not observed:
        raise ValueError("no training labels for predictor")
    return (
        sorted(observed | set(canonical), key=str)
        if observed <= set(canonical)
        else sorted(observed, key=str)
    )


def run_evaluation_from_csv(
    workflow_name,
    csv_path,
    dataset_source,
    label_cols,
    meta_cols,
    seed=0,
    alpha=0.1,
    alpha_allocation="uniform",
    ratios=(0.6, 0.2, 0.2),
    filter_dme_subset=False,
    observation_cols=None,
    allow_repartition=False,
    **kwargs,
):
    if filter_dme_subset:
        raise ValueError(
            "filter_dme_subset removed: retain missing labels and report eligibility explicitly"
        )
    samples = load_samples_from_csv(
        csv_path,
        dataset_source,
        label_cols=label_cols,
        meta_cols=meta_cols,
        observation_cols=observation_cols,
    )
    splits = make_splits(samples, seed, ratios, allow_repartition=allow_repartition)
    if workflow_name == "dr_workflow":
        workflow, label, canonical = DRWorkflow(), "dr_severity", ["mild", "moderate", "severe"]
    elif workflow_name == "glaucoma_workflow":
        workflow, label, canonical = GlaucomaWorkflow(), "glaucoma_risk", ["low", "high"]
    else:
        raise ValueError("unsupported workflow")
    train = [s for s in samples if s.sample_id in splits["train"]]
    predictor = TrivialLabelPredictor(label, _infer_class_values(train, label, canonical))
    return evaluate_experiment(
        workflow,
        samples,
        splits,
        predictor,
        alpha=alpha,
        alpha_allocation=alpha_allocation,
        seed=seed,
        split_protocol="explicit_repartition"
        if allow_repartition
        else "official_partition"
        if any(s.meta.get("split_hint") for s in samples)
        else "random_groups",
        **kwargs,
    )
