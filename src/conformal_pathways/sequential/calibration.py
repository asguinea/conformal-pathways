"""Fixed-budget split conformal calibration along result-aware reference histories."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from conformal_pathways.conformal.thresholds import allocate_alpha, compute_stage_thresholds
from conformal_pathways.data.schema import validate_samples
from conformal_pathways.safety.oracle import label_unavailability
from conformal_pathways.safety.oracle_policy import oracle_pathway

from .engine import ScoreConfig, StageFilter
from .simulation import reference_scores, validate_scenarios


@dataclass(frozen=True)
class Calibration:
    stage_filter: StageFilter
    budgets: tuple[float, ...]
    group_ids: tuple[str, ...]
    excluded_group_ids: tuple[str, ...]
    scores: tuple[tuple[float, ...], ...]
    mechanism: str

    def to_dict(self):
        return {
            "filter": self.stage_filter.to_dict(),
            "budgets": list(self.budgets),
            "group_ids": list(self.group_ids),
            "excluded_group_ids": list(self.excluded_group_ids),
            "group_scores_by_stage": [list(v) for v in self.scores],
            "mechanism": self.mechanism,
        }


def calibrate(
    workflow,
    samples,
    distributions,
    scenarios,
    *,
    alpha=0.1,
    allocation="uniform",
    score=ScoreConfig(),
    training_groups,
):
    """Caller supplies predictions from one model fitted only on training groups.

    Training groups must be declared; the integrated evaluator handles fitting
    and prediction consistently. Raw distributions alone cannot prove provenance.
    """
    validate_samples(samples)
    if not samples:
        raise ValueError("no fully rule-evaluable calibration groups")
    mechanism = validate_scenarios(workflow, samples, scenarios)
    if set(distributions) != {s.sample_id for s in samples}:
        raise ValueError("calibration distributions must match sample IDs")
    budgets = allocate_alpha(alpha, workflow.num_stages, allocation)
    groups = defaultdict(list)
    reasons = {s.sample_id: label_unavailability(workflow.name, s.labels) for s in samples}
    for sample in samples:
        groups[sample.group_id()].append(sample)
    if set(groups) & set(training_groups):
        raise ValueError("calibration groups overlap training groups")
    included, excluded = [], []
    scores = {stage: [] for stage in range(1, workflow.num_stages + 1)}
    for gid, members in sorted(groups.items()):
        if any(reasons[s.sample_id] for s in members):
            excluded.append(gid)
            continue
        vectors = [
            reference_scores(
                workflow,
                s.prediction_input(),
                distributions[s.sample_id],
                oracle_pathway(workflow, s.labels),
                scenarios[s.sample_id],
                score,
            )
            for s in members
        ]
        included.append(gid)
        for t in scores:
            scores[t].append(max(v[t - 1] for v in vectors))
    if not included:
        raise ValueError("no fully rule-evaluable calibration groups")
    thresholds = compute_stage_thresholds(scores, alpha, allocation)
    return Calibration(
        StageFilter(workflow.name, tuple(thresholds.values()), score),
        tuple(budgets.values()),
        tuple(included),
        tuple(excluded),
        tuple(tuple(v) for v in scores.values()),
        mechanism,
    )
