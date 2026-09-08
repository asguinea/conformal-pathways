"""Versioned illustrative rules. These predicates do not measure clinical safety."""

from __future__ import annotations

from conformal_pathways.data.loaders import normalize_dr_severity, normalize_glaucoma_risk

RULE_VERSION = "toy-rules-v2"


class MissingLabelError(ValueError):
    pass


def required_labels(workflow_name):
    if workflow_name == "dr_workflow":
        return ("dr_severity", "dme_positive")
    if workflow_name == "glaucoma_workflow":
        return ("glaucoma_risk",)
    raise ValueError(f"Unsupported workflow {workflow_name!r}")


def label_unavailability(workflow_name, labels):
    keys = required_labels(workflow_name)
    if workflow_name == "dr_workflow":
        if labels.get("dr_severity") is not None:
            normalize_dr_severity(labels["dr_severity"])
        if labels.get("dme_positive") is not None and not isinstance(labels["dme_positive"], bool):
            raise ValueError("dme_positive must be a normalized Boolean")
    elif labels.get("glaucoma_risk") is not None:
        normalize_glaucoma_risk(labels["glaucoma_risk"])
    missing = [key for key in keys if labels.get(key) is None]
    return "missing:" + ",".join(missing) if missing else None


def severe_dr(value):
    return normalize_dr_severity(value) in {3, 4, "severe"}


def pathway_contains_action(pathway, name):
    return any(action.name == name for action in pathway.actions)


def is_safe_dr(sample_meta, final_state, pathway):
    from conformal_pathways.workflows import DRWorkflow

    if len(pathway) != 3:
        raise ValueError("rule evaluation requires a complete pathway")
    final_state = DRWorkflow().rollout({}, pathway)
    if label_unavailability("dr_workflow", sample_meta):
        return None
    positive = sample_meta["dme_positive"]
    severe = severe_dr(sample_meta["dr_severity"])
    management = final_state.get("management")
    weeks = final_state.get("followup_weeks")
    if positive and not pathway_contains_action(pathway, "order_OCT"):
        return False
    if (positive or severe) and (management == "monitor" or weeks == 24):
        return False
    if not positive and management == "anti_VEGF":
        return False
    return True


def is_safe_glaucoma(sample_meta, final_state, pathway):
    from conformal_pathways.workflows import GlaucomaWorkflow

    if len(pathway) != 3:
        raise ValueError("rule evaluation requires a complete pathway")
    final_state = GlaucomaWorkflow().rollout({}, pathway)
    if label_unavailability("glaucoma_workflow", sample_meta):
        return None
    high = normalize_glaucoma_risk(sample_meta["glaucoma_risk"]) == "high"
    if high:
        return (
            pathway_contains_action(pathway, "order_extra_tests")
            and final_state.get("management") != "monitor"
            and final_state.get("followup_weeks") != 24
        )
    return final_state.get("management") != "treat"


def is_safe(workflow_name, sample_meta, final_state, pathway):
    if workflow_name == "dr_workflow":
        return is_safe_dr(sample_meta, final_state, pathway)
    if workflow_name == "glaucoma_workflow":
        return is_safe_glaucoma(sample_meta, final_state, pathway)
    raise ValueError(f"Unsupported workflow {workflow_name!r}")


def is_guideline_consistent(*args, **kwargs):
    raise ValueError("guideline mode removed; only explicitly defined toy-rules-v2 are supported")


def is_guideline_consistent_dr(*args, **kwargs):
    return is_guideline_consistent(*args, **kwargs)


def is_guideline_consistent_glaucoma(*args, **kwargs):
    return is_guideline_consistent(*args, **kwargs)
