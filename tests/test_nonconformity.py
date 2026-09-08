from __future__ import annotations

from conformal_pathways.scoring import rule_penalty_obs, score_action
from conformal_pathways.workflows.core import Action, State


def test_dr_stage1_penalties() -> None:
    state = State(observed={"dme_status": "unknown"})

    assert rule_penalty_obs("dr_workflow", 1, state, Action("no_OCT")) == 1.0
    assert rule_penalty_obs("dr_workflow", 1, state, Action("order_OCT")) == 0.0


def test_dr_stage2_penalties() -> None:
    state = State(observed={"dme_status": "revealed_positive"})

    assert rule_penalty_obs("dr_workflow", 2, state, Action("monitor")) == 1.0
    assert rule_penalty_obs("dr_workflow", 2, state, Action("anti_VEGF")) == 0.0


def test_dr_stage3_penalties() -> None:
    state = State(observed={"dme_status": "revealed_positive"})

    assert rule_penalty_obs("dr_workflow", 3, state, Action("followup", {"weeks": 24})) == 1.0
    assert rule_penalty_obs("dr_workflow", 3, state, Action("followup", {"weeks": 12})) == 0.0


def test_glaucoma_penalties() -> None:
    state = State(observed={"glaucoma_risk": "high"})

    assert rule_penalty_obs("glaucoma_workflow", 1, state, Action("no_extra_tests")) == 1.0
    assert rule_penalty_obs("glaucoma_workflow", 2, state, Action("monitor")) == 1.0
    assert rule_penalty_obs("glaucoma_workflow", 3, state, Action("followup", {"weeks": 24})) == 1.0


def test_score_action_combines_action_nonconformity_and_penalty() -> None:
    state = State(observed={"dme_status": "unknown"})

    score = score_action(
        workflow_name="dr_workflow",
        stage=1,
        state=state,
        action=Action("no_OCT"),
        action_probability=0.75,
        w_u=2.0,
        w_r=3.0,
    )

    assert score == 2.0 * 0.25 + 3.0 * 1.0
