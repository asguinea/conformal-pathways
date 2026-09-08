from __future__ import annotations

import math
from typing import Any

from conformal_pathways.data import Sample
from conformal_pathways.models import Predictor
from conformal_pathways.safety.oracle_policy import oracle_pathway
from conformal_pathways.scoring import score_action
from conformal_pathways.workflows.core import Action


def oracle_actions_by_stage(workflow, sample_meta: dict[str, Any]) -> list[Action]:
    pathway = oracle_pathway(workflow, sample_meta, safety_mode="strict")
    actions = list(pathway.actions)
    return actions


def collect_oracle_scores_by_stage(
    workflow,
    samples: list[Sample],
    predictor: Predictor,
    workflow_name: str,
    w_u: float = 1.0,
    w_r: float = 1.0,
) -> dict[int, list[float]]:
    num_stages = workflow.num_stages
    scores_by_stage: dict[int, list[float]] = {stage: [] for stage in range(1, num_stages + 1)}

    for sample in samples:
        sample_meta = {**sample.labels, **sample.meta}
        state = workflow.initial_state(sample_meta)
        actions = oracle_actions_by_stage(workflow, sample_meta)
        if len(actions) != num_stages:
            raise ValueError(
                f"oracle actions length {len(actions)} does not match num_stages={num_stages}"
            )

        model_uncertainty = predictor.uncertainty([sample])[0]
        for stage in range(1, num_stages + 1):
            action = actions[stage - 1]
            score = score_action(
                workflow_name=workflow_name,
                stage=stage,
                state=state,
                action=action,
                model_uncertainty=model_uncertainty,
                w_u=w_u,
                w_r=w_r,
            )
            if math.isnan(score):
                raise ValueError(f"NaN score encountered at stage {stage}")

            scores_by_stage[stage].append(score)
            state = workflow.transition(stage, state, action, sample_meta)

    expected_keys = set(range(1, num_stages + 1))
    if set(scores_by_stage) != expected_keys:
        raise ValueError(
            f"scores_by_stage keys mismatch: expected {expected_keys}, got {set(scores_by_stage)}"
        )

    return scores_by_stage
