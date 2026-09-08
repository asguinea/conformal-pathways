from __future__ import annotations

from typing import Any

from conformal_pathways.data import Sample
from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.experiment import evaluate_experiment
from conformal_pathways.features.cache import ids_path_for
from conformal_pathways.features.extract_embeddings import (
    extract_embeddings_from_manifest,
)
from conformal_pathways.models.embedding_predictor import EmbeddingLogRegPredictor
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow


def samples_from_manifest_csv(
    manifest_csv: str, observation_cols: dict[str, str] | None = None
) -> list[Sample]:
    from conformal_pathways.data.loaders import load_samples_from_csv

    return load_samples_from_csv(
        manifest_csv,
        None,
        label_cols=["dr_severity", "dme_positive", "glaucoma_risk"],
        meta_cols=["patient_id", "eye_id", "global_patient_id", "group_provenance"],
        observation_cols=observation_cols,
    )


def _infer_dr_classes(train_samples: list[Sample]) -> list[Any]:
    observed = [
        sample.get_label("dr_severity")
        for sample in train_samples
        if sample.has_label("dr_severity")
    ]
    observed = [value for value in observed if value is not None]
    if not observed:
        raise ValueError("no dr_severity labels found in train split")

    int_like = all(isinstance(value, (int,)) and not isinstance(value, bool) for value in observed)
    if int_like:
        return sorted(set(observed))
    return sorted(set(observed), key=lambda value: str(value))


def _infer_glaucoma_classes(train_samples: list[Sample]) -> list[Any]:
    observed = [
        sample.get_label("glaucoma_risk")
        for sample in train_samples
        if sample.has_label("glaucoma_risk")
    ]
    observed = [value for value in observed if value is not None]
    if not observed:
        raise ValueError("no glaucoma_risk labels found in train split")

    lowered = {str(value).lower() for value in observed}
    if "low" in lowered and "high" in lowered:
        return ["low", "high"]
    return sorted(set(observed), key=lambda value: str(value))


def run_evaluation_with_embeddings(
    workflow_name,
    manifest_csv,
    dataset_root,
    seed=0,
    alpha=0.1,
    alpha_allocation="uniform",
    ratios=(0.6, 0.2, 0.2),
    embeddings_out_path="artifacts/embeddings/tmp_embeddings.npy",
    batch_size=32,
    prefer_mps=True,
    max_items=None,
    filter_dme_subset=False,
    force_extract=False,
    weights="IMAGENET1K_V2",
    random_seed=None,
    device=None,
    allow_repartition=False,
    observation_cols=None,
    **kwargs,
):
    if filter_dme_subset:
        raise ValueError("filter_dme_subset removed; keep missing labels and report eligibility")
    if max_items is not None:
        raise ValueError(
            "evaluation subsampling requires an explicit group-preserving manifest, not max_items"
        )
    samples = samples_from_manifest_csv(manifest_csv, observation_cols)
    splits = make_splits(samples, seed, ratios, allow_repartition=allow_repartition)
    if any(not ids for ids in splits.values()):
        raise ValueError("insufficient split sizes for train/cal/test")
    train = [s for s in samples if s.sample_id in splits["train"]]
    if workflow_name == "dr_workflow":
        workflow, label, classes = DRWorkflow(), "dr_severity", _infer_dr_classes(train)
    elif workflow_name == "glaucoma_workflow":
        workflow, label, classes = (
            GlaucomaWorkflow(),
            "glaucoma_risk",
            _infer_glaucoma_classes(train),
        )
    else:
        raise ValueError("unsupported workflow")
    stats = extract_embeddings_from_manifest(
        manifest_csv,
        dataset_root,
        embeddings_out_path,
        batch_size=batch_size,
        prefer_mps=prefer_mps,
        weights=weights,
        random_seed=random_seed,
        force_extract=force_extract,
        device=device,
    )
    predictor = EmbeddingLogRegPredictor(
        stats["out_path"],
        str(ids_path_for(stats["out_path"])),
        {s.sample_id: s.get_label(label) for s in train},
        classes,
    )
    result = evaluate_experiment(
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
    result["embedding_provenance"] = predictor.cache_metadata
    return result
