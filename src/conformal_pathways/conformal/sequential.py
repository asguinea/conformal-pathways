"""Stage-filtered open-loop pathways scored from entry observations only."""

from __future__ import annotations

import math

from conformal_pathways.safety.oracle_policy import enumerate_all_pathways
from conformal_pathways.scoring.nonconformity import score_pathway


def build_prediction_set(
    workflow, sample, predictor, workflow_name, thresholds, w_u=1.0, w_r=1.0, max_paths=None
):
    if workflow_name != workflow.name:
        raise ValueError("workflow_name mismatch")
    if max_paths is not None:
        raise ValueError(
            "max_paths truncation is removed because it can invalidate reference inclusion"
        )
    if set(thresholds) != set(range(1, workflow.num_stages + 1)):
        raise ValueError("threshold keys must match all stages")
    if any(math.isnan(q) or q == -math.inf for q in thresholds.values()):
        raise ValueError("thresholds must be finite or positive infinity")
    inputs = sample.prediction_input()
    paths = enumerate_all_pathways(workflow, inputs.observed_values())
    # The exact unpruned baseline needs neither model inference nor calibration.
    if all(q == math.inf for q in thresholds.values()):
        return paths
    return [
        p
        for p in paths
        if all(
            score <= thresholds[t]
            for t, score in enumerate(score_pathway(workflow, inputs, predictor, p, w_u, w_r), 1)
        )
    ]
