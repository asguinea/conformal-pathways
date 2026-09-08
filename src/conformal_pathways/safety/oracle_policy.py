"""Privileged reference targets, for evaluation/calibration only."""

from __future__ import annotations

from conformal_pathways.data.loaders import normalize_glaucoma_risk
from conformal_pathways.safety.oracle import MissingLabelError, label_unavailability, severe_dr
from conformal_pathways.workflows.core import Action, Pathway


def enumerate_all_pathways(workflow, entry_observations=None):
    current = [(workflow.initial_state(entry_observations or {}), Pathway())]
    for stage in range(1, workflow.num_stages + 1):
        current = [
            (workflow.transition(stage, state, action, None), path.append(action))
            for state, path in current
            for action in workflow.actions_at(stage, state)
        ]
    return [path for _, path in current]


def oracle_pathway(workflow, sample_meta, safety_mode="strict"):
    if safety_mode != "strict":
        raise ValueError("only the versioned strict toy rule mode is supported")
    reason = label_unavailability(workflow.name, sample_meta)
    if reason:
        raise MissingLabelError(reason)
    if workflow.name == "dr_workflow":
        positive = sample_meta["dme_positive"]
        escalate = positive or severe_dr(sample_meta["dr_severity"])
        names = ("order_OCT" if positive else "no_OCT", "refer_retina" if escalate else "monitor")
    else:
        escalate = normalize_glaucoma_risk(sample_meta["glaucoma_risk"]) == "high"
        names = (
            "order_extra_tests" if escalate else "no_extra_tests",
            "refer_glaucoma" if escalate else "monitor",
        )
    return Pathway(
        [Action(names[0]), Action(names[1]), Action("followup", {"weeks": 4 if escalate else 12})]
    )
