"""Reference-path scores aggregated at the declared independent group unit."""

from __future__ import annotations

from collections import defaultdict

from conformal_pathways.data import validate_samples
from conformal_pathways.safety.oracle import label_unavailability
from conformal_pathways.safety.oracle_policy import oracle_pathway
from conformal_pathways.scoring.nonconformity import score_pathway


def oracle_actions_by_stage(workflow, sample_meta):
    return list(oracle_pathway(workflow, sample_meta).actions)


def collect_oracle_scores_by_stage(workflow, samples, predictor, workflow_name, w_u=1.0, w_r=1.0):
    if workflow_name != workflow.name:
        raise ValueError("workflow_name mismatch")
    validate_samples(samples)
    groups = defaultdict(list)
    for sample in samples:
        groups[sample.group_id()].append(sample)
    if set(groups) & set(getattr(predictor, "training_groups", ())):
        raise ValueError("calibration groups overlap predictor training groups")
    result = {t: [] for t in range(1, workflow.num_stages + 1)}
    for gid in sorted(groups):
        members = groups[gid]
        # Calibration targets the population of fully rule-evaluable groups.
        # Never silently treat unlabelled members as independent successful cases.
        if any(label_unavailability(workflow.name, s.labels) for s in members):
            continue
        vectors = [
            score_pathway(workflow, s, predictor, oracle_pathway(workflow, s.labels), w_u, w_r)
            for s in members
        ]
        for t in result:
            result[t].append(max(row[t - 1] for row in vectors))
    if not result[1]:
        raise ValueError("no fully rule-evaluable calibration groups")
    return result
