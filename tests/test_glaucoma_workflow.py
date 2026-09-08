import pytest

from conformal_pathways.workflows.core import Action
from conformal_pathways.workflows.glaucoma import GlaucomaWorkflow


def test_initial_state_defaults() -> None:
    wf = GlaucomaWorkflow()
    state = wf.initial_state({"glaucoma_risk": "high"})

    assert state.get("glaucoma_risk") == "high"
    assert state.get("tests_ordered") == []
    assert state.get("management") is None
    assert state.get("followup_weeks") is None


def test_order_extra_tests_sets_tests() -> None:
    wf = GlaucomaWorkflow()
    sample_meta = {"glaucoma_risk": "high"}
    state = wf.initial_state(sample_meta)

    next_state = wf.transition(1, state, Action("order_extra_tests"), None)

    assert next_state.get("tests_ordered") == ["OCT_RNFL", "VF"]


def test_no_extra_tests_leaves_empty() -> None:
    wf = GlaucomaWorkflow()
    sample_meta = {"glaucoma_risk": "high"}
    state = wf.initial_state(sample_meta)

    next_state = wf.transition(1, state, Action("no_extra_tests"), None)

    assert next_state.get("tests_ordered") == []


def test_followup_invalid_weeks_raises() -> None:
    wf = GlaucomaWorkflow()
    sample_meta = {"glaucoma_risk": "high"}
    state = wf.initial_state(sample_meta)

    with pytest.raises(ValueError, match="admissible"):
        wf.transition(3, state, Action("followup", {"weeks": 10}), None)


def test_transition_does_not_mutate_original_state() -> None:
    wf = GlaucomaWorkflow()
    sample_meta = {"glaucoma_risk": "high"}
    state0 = wf.initial_state(sample_meta)

    _ = wf.transition(1, state0, Action("order_extra_tests"), None)

    assert state0.get("glaucoma_risk") == "high"
    assert state0.get("tests_ordered") == []
    assert state0.get("management") is None
    assert state0.get("followup_weeks") is None


def test_stage_action_validation_raises() -> None:
    wf = GlaucomaWorkflow()
    sample_meta = {"glaucoma_risk": "high"}
    state = wf.initial_state(sample_meta)

    with pytest.raises(ValueError, match="admissible"):
        wf.transition(1, state, Action("treat"), None)
