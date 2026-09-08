from __future__ import annotations

from typing import Any

from conformal_pathways.safety.oracle import is_guideline_consistent, is_safe
from conformal_pathways.workflows.core import Pathway, Workflow


def enumerate_all_pathways(workflow: Workflow) -> list[Pathway]:
    sample_meta: dict[str, Any] = {}
    initial_state = workflow.initial_state(sample_meta)
    pathways: list[Pathway] = []

    def _expand(stage: int, state, path: Pathway) -> None:
        if stage > workflow.num_stages:
            pathways.append(path)
            return

        for action in workflow.actions_at(stage, state):
            next_state = workflow.transition(stage, state, action, sample_meta)
            _expand(stage + 1, next_state, path.append(action))

    _expand(stage=1, state=initial_state, path=Pathway())
    return pathways


def _followup_weeks(pathway: Pathway) -> int:
    if not pathway.actions:
        return 10**9
    return int(pathway.actions[-1].params.get("weeks", 10**9))


def _pathway_burden(pathway: Pathway) -> int:
    diagnostics = {"order_OCT", "order_extra_tests"}
    interventions = {"anti_VEGF", "refer_retina", "treat", "refer_glaucoma"}
    return sum(1 for action in pathway.actions if action.name in diagnostics | interventions)


def _matches_guideline_default(
    workflow_name: str,
    sample_meta: dict[str, Any],
    pathway: Pathway,
) -> bool:
    if len(pathway.actions) != 3:
        return False

    stage1 = pathway.actions[0].name
    stage2 = pathway.actions[1].name
    followup_weeks = _followup_weeks(pathway)

    if workflow_name == "dr_workflow":
        if sample_meta.get("dme_positive") is True:
            return (
                stage1 == "order_OCT"
                and stage2 in {"anti_VEGF", "refer_retina"}
                and followup_weeks == 4
            )
        if sample_meta.get("dme_positive") is False:
            return (
                stage1 in {"no_OCT", "order_OCT"}
                and stage2 == "monitor"
                and followup_weeks == 12
            )
        return False

    if workflow_name == "glaucoma_workflow":
        if sample_meta.get("glaucoma_risk") == "high":
            return (
                stage1 == "order_extra_tests"
                and stage2 in {"treat", "refer_glaucoma"}
                and followup_weeks == 4
            )
        return stage2 == "monitor" and followup_weeks == 12

    return False


def oracle_pathway(
    workflow: Workflow,
    sample_meta: dict[str, Any],
    safety_mode: str = "strict",
) -> Pathway:
    pathways = enumerate_all_pathways(workflow)

    safe_pathways: list[Pathway] = []
    for pathway in pathways:
        final_state = workflow.rollout(sample_meta, pathway)
        if safety_mode == "strict":
            ok = is_safe(workflow.name, sample_meta, final_state, pathway)
        elif safety_mode == "guideline":
            ok = is_guideline_consistent(workflow.name, sample_meta, final_state, pathway)
        else:
            raise ValueError(
                f"Unsupported safety_mode '{safety_mode}', expected 'strict' or 'guideline'"
            )

        if ok:
            safe_pathways.append(pathway)

    if not safe_pathways:
        raise ValueError("No safe pathways found for the provided sample_meta")

    def _sort_key(pathway: Pathway) -> tuple[Any, ...]:
        return (
            0 if _matches_guideline_default(workflow.name, sample_meta, pathway) else 1,
            _followup_weeks(pathway),
            _pathway_burden(pathway),
            tuple(pathway.to_names()),
            tuple(tuple(sorted(action.params.items())) for action in pathway.actions),
        )

    return min(safe_pathways, key=_sort_key)
