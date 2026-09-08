from __future__ import annotations

from typing import Any

from conformal_pathways.workflows.core import Pathway, State


def pathway_contains_action(pathway: Pathway, name: str) -> bool:
    return any(action.name == name for action in pathway.actions)


def is_safe_dr(sample_meta: dict[str, Any], final_state: State, pathway: Pathway) -> bool:
    dme_positive = sample_meta.get("dme_positive") is True

    if dme_positive and not pathway_contains_action(pathway, "order_OCT"):
        return False
    if dme_positive and final_state.get("followup_weeks") == 24:
        return False
    if dme_positive and final_state.get("management") == "monitor":
        return False
    if sample_meta.get("dme_positive") is False and final_state.get("management") == "anti_VEGF":
        return False

    return True


def is_safe_glaucoma(
    sample_meta: dict[str, Any],
    final_state: State,
    pathway: Pathway,
) -> bool:
    del sample_meta, pathway
    if (
        final_state.get("glaucoma_risk") == "high"
        and final_state.get("followup_weeks") == 24
        and final_state.get("management") == "monitor"
        and final_state.get("tests_ordered") == []
    ):
        return False
    return True


def is_guideline_consistent_dr(
    sample_meta: dict[str, Any],
    final_state: State,
    pathway: Pathway,
) -> bool:
    if is_safe_dr(sample_meta, final_state, pathway):
        return True

    # Looser than strict safety: allow anti-VEGF despite dme_positive=False.
    return (
        sample_meta.get("dme_positive") is False
        and final_state.get("management") == "anti_VEGF"
    )


def is_guideline_consistent_glaucoma(
    sample_meta: dict[str, Any],
    final_state: State,
    pathway: Pathway,
) -> bool:
    if is_safe_glaucoma(sample_meta, final_state, pathway):
        return True

    # Looser than strict safety: allow this pattern when testing is not feasible.
    return (
        sample_meta.get("unable_to_test") is True
        and final_state.get("glaucoma_risk") == "high"
        and final_state.get("followup_weeks") == 24
        and final_state.get("management") == "monitor"
        and final_state.get("tests_ordered") == []
    )


def is_safe(
    workflow_name: str,
    sample_meta: dict[str, Any],
    final_state: State,
    pathway: Pathway,
) -> bool:
    if workflow_name == "dr_workflow":
        return is_safe_dr(sample_meta, final_state, pathway)
    if workflow_name == "glaucoma_workflow":
        return is_safe_glaucoma(sample_meta, final_state, pathway)
    raise ValueError(f"Unsupported workflow '{workflow_name}' for safety dispatch")


def is_guideline_consistent(
    workflow_name: str,
    sample_meta: dict[str, Any],
    final_state: State,
    pathway: Pathway,
) -> bool:
    if workflow_name == "dr_workflow":
        return is_guideline_consistent_dr(sample_meta, final_state, pathway)
    if workflow_name == "glaucoma_workflow":
        return is_guideline_consistent_glaucoma(sample_meta, final_state, pathway)
    raise ValueError(
        f"Unsupported workflow '{workflow_name}' for guideline-consistency dispatch"
    )
