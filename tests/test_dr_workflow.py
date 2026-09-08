import pytest

from conformal_pathways.workflows.core import Action
from conformal_pathways.workflows.dr import (
    DME_STATUS_REVEALED_POSITIVE,
    DME_STATUS_UNKNOWN,
    DRWorkflow,
)


def test_initial_state_defaults() -> None:
    wf = DRWorkflow()
    state = wf.initial_state({"dr_severity": "moderate"})

    assert state.get("dr_severity") == "moderate"
    assert state.get("dme_status") == DME_STATUS_UNKNOWN
    assert state.get("oct_ordered") is False
    assert state.get("management") is None
    assert state.get("followup_weeks") is None


def test_oct_reveals_dme_when_available() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": True,
        "dme_positive": True,
    }
    state = wf.initial_state(sample_meta)

    next_state = wf.transition(1, state, Action("order_OCT"), sample_meta)

    assert next_state.get("oct_ordered") is True
    assert next_state.get("dme_status") == DME_STATUS_REVEALED_POSITIVE


def test_oct_does_not_reveal_when_unavailable() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": False,
        "dme_positive": True,
    }
    state = wf.initial_state(sample_meta)

    next_state = wf.transition(1, state, Action("order_OCT"), sample_meta)

    assert next_state.get("oct_ordered") is True
    assert next_state.get("dme_status") == DME_STATUS_UNKNOWN


def test_followup_set() -> None:
    wf = DRWorkflow()
    sample_meta = {"dr_severity": "moderate"}
    state = wf.initial_state(sample_meta)

    next_state = wf.transition(3, state, Action("followup", {"weeks": 12}), sample_meta)

    assert next_state.get("followup_weeks") == 12


def test_transition_does_not_mutate_original_state() -> None:
    wf = DRWorkflow()
    sample_meta = {
        "dr_severity": "moderate",
        "dme_label_available": True,
        "dme_positive": True,
    }
    state0 = wf.initial_state(sample_meta)

    _ = wf.transition(1, state0, Action("order_OCT"), sample_meta)

    assert state0.get("dr_severity") == "moderate"
    assert state0.get("dme_status") == DME_STATUS_UNKNOWN
    assert state0.get("oct_ordered") is False
    assert state0.get("management") is None
    assert state0.get("followup_weeks") is None


def test_followup_invalid_weeks_raises() -> None:
    wf = DRWorkflow()
    sample_meta = {"dr_severity": "moderate"}
    state = wf.initial_state(sample_meta)

    with pytest.raises(ValueError, match="Invalid followup weeks"):
        wf.transition(3, state, Action("followup", {"weeks": 10}), sample_meta)
