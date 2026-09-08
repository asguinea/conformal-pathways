from __future__ import annotations

from conformal_pathways.data import Sample
from conformal_pathways.models import Predictor
from conformal_pathways.scoring import score_action
from conformal_pathways.workflows.core import Pathway, Workflow


def _pathway_sort_key(path: Pathway) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    return tuple(
        (
            action.name,
            tuple((key, repr(value)) for key, value in sorted(action.params.items())),
        )
        for action in path.actions
    )


def build_prediction_set(
    workflow: Workflow,
    sample: Sample,
    predictor: Predictor,
    workflow_name: str,
    thresholds: dict[int, float],
    w_u: float = 1.0,
    w_r: float = 1.0,
    max_paths: int | None = None,
) -> list[Pathway]:
    sample_meta = {**sample.labels, **sample.meta}
    num_stages = workflow.num_stages
    expected_keys = set(range(1, num_stages + 1))
    if set(thresholds) != expected_keys:
        raise ValueError(f"threshold keys must be {expected_keys}, got {set(thresholds)}")

    model_uncertainty = predictor.uncertainty([sample])[0]
    current: list[tuple] = [(workflow.initial_state(sample_meta), Pathway())]

    for stage in range(1, num_stages + 1):
        new: list[tuple] = []
        for state, path in current:
            actions = workflow.actions_at(stage, state)
            for action in actions:
                score = score_action(
                    workflow_name=workflow_name,
                    stage=stage,
                    state=state,
                    action=action,
                    model_uncertainty=model_uncertainty,
                    w_u=w_u,
                    w_r=w_r,
                )
                if score <= thresholds[stage]:
                    next_state = workflow.transition(stage, state, action, sample_meta)
                    new.append((next_state, path.append(action)))

        if max_paths is not None and len(new) > max_paths:
            new = sorted(new, key=lambda item: _pathway_sort_key(item[1]))[:max_paths]
        current = new

    return [path for _, path in current]
