import pytest

from conformal_pathways.data import Observation
from conformal_pathways.workflows.core import Action, DiagnosticResult
from conformal_pathways.workflows.dr import DRWorkflow


def test_initial_state_defaults():
    state = DRWorkflow().initial_state({"dr_severity": "moderate"})
    assert state.get("dr_severity") == "moderate"
    assert state.get("dme_status") == "unknown"
    assert state.get("oct_ordered") is False
    assert state.get("management") is None
    assert state.get("followup_weeks") is None


@pytest.mark.parametrize(
    "value,status", [(True, "revealed_positive"), (False, "revealed_negative"), (None, "unknown")]
)
def test_explicit_result_updates_a_new_state(value, status):
    wf = DRWorkflow()
    initial = wf.initial_state({})
    result = DiagnosticResult("order_OCT", Observation(value, "synthetic_result", 1))
    final = wf.transition(1, initial, Action("order_OCT"), result)
    assert final.get("dme_status") == status
    assert final.get("oct_ordered") is True
    assert initial.get("dme_status") == "unknown"
    assert initial.get("oct_ordered") is False


def test_followup_set():
    wf = DRWorkflow()
    state = wf.initial_state({})
    assert (
        wf.transition(3, state, Action("followup", {"weeks": 12}), None).get("followup_weeks") == 12
    )


def test_followup_invalid_weeks_raises():
    wf = DRWorkflow()
    with pytest.raises(ValueError, match="admissible"):
        wf.transition(3, wf.initial_state({}), Action("followup", {"weeks": 10}), None)
