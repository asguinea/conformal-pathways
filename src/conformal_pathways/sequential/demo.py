"""Small generated-data correctness example; not a benchmark."""

from conformal_pathways.data.splits import make_splits
from conformal_pathways.eval.runner import (
    make_synthetic_samples_dr,
    make_synthetic_samples_glaucoma,
)
from conformal_pathways.models.trivial import TrivialLabelPredictor
from conformal_pathways.workflows import DRWorkflow, GlaucomaWorkflow

from .evaluation import evaluate_sequential
from .simulation import proxy_scenarios


def run_demo(workflow_name="dr", n=100, seed=0, alpha=0.1):
    if n < 20:
        raise ValueError("demo needs at least 20 samples")
    if workflow_name == "dr":
        workflow, samples = DRWorkflow(), make_synthetic_samples_dr(n, seed)
        predictor = TrivialLabelPredictor("dr_severity", ["mild", "moderate", "severe"])
    elif workflow_name == "glaucoma":
        workflow, samples = GlaucomaWorkflow(), make_synthetic_samples_glaucoma(n, seed)
        predictor = TrivialLabelPredictor("glaucoma_risk", ["low", "high"])
    else:
        raise ValueError("unsupported workflow")
    splits = make_splits(samples, seed)
    scenarios = proxy_scenarios(
        workflow, [s for s in samples if s.sample_id not in splits["train"]]
    )
    return evaluate_sequential(
        workflow,
        samples,
        splits,
        predictor,
        scenarios,
        alpha=alpha,
        model_spec={"type": "class_prior", "seed": seed, "smoothing": predictor.smoothing},
    )
