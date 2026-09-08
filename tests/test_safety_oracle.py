from conformal_pathways.safety.oracle import is_safe_dr
from conformal_pathways.workflows.core import Action, Pathway
from conformal_pathways.workflows.dr import DRWorkflow


def test_dr_no_oct_with_dme_positive_is_unsafe() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": True,
        "dme_positive": True,
    }
    pathway = Pathway(
        actions=[
            Action("no_OCT"),
            Action("refer_retina"),
            Action("followup", {"weeks": 4}),
        ]
    )

    final_state = wf.rollout(sample_meta, pathway)

    assert is_safe_dr(sample_meta, final_state, pathway) is False


def test_dr_oct_monitor_followup_24_is_unsafe() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": True,
        "dme_positive": True,
    }
    pathway = Pathway(
        actions=[
            Action("order_OCT"),
            Action("monitor"),
            Action("followup", {"weeks": 24}),
        ]
    )

    final_state = wf.rollout(sample_meta, pathway)

    assert is_safe_dr(sample_meta, final_state, pathway) is False


def test_dr_oct_anti_vegf_followup_4_is_safe() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": True,
        "dme_positive": True,
    }
    pathway = Pathway(
        actions=[
            Action("order_OCT"),
            Action("anti_VEGF"),
            Action("followup", {"weeks": 4}),
        ]
    )

    final_state = wf.rollout(sample_meta, pathway)

    assert is_safe_dr(sample_meta, final_state, pathway) is True
