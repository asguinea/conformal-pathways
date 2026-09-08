import pytest

from conformal_pathways.workflows.core import Action, Pathway, State, Workflow


def test_action_hashing() -> None:
    a1 = Action(name="predict", params={"k": 1, "mode": "fast"})
    a2 = Action(name="predict", params={"mode": "fast", "k": 1})

    assert len({a1, a2}) == 1


def test_pathway_append_immutable() -> None:
    p1 = Pathway(actions=[Action(name="a1")])
    p2 = p1.append(Action(name="a2"))

    assert p1.to_names() == ["a1"]
    assert p2.to_names() == ["a1", "a2"]


def test_validate_stage_index() -> None:
    class DummyWorkflow(Workflow):
        def initial_state(self, sample_meta: dict) -> State:
            return State(observed={})

        def actions_at(self, stage: int, state: State) -> list[Action]:
            return []

        def transition(self, stage: int, state: State, action: Action, sample_meta: dict) -> State:
            return state

    wf = DummyWorkflow(name="dummy", num_stages=2)

    with pytest.raises(ValueError):
        wf.validate_stage_index(0)

    with pytest.raises(ValueError):
        wf.validate_stage_index(3)


def test_rollout_dummy_workflow() -> None:
    class DummyWorkflow(Workflow):
        def initial_state(self, sample_meta: dict) -> State:
            return State(observed={"sum": sample_meta.get("offset", 0)})

        def actions_at(self, stage: int, state: State) -> list[Action]:
            return [Action(name="add", params={"value": stage})]

        def transition(self, stage: int, state: State, action: Action, sample_meta: dict) -> State:
            next_state = state.copy()
            next_state.set("sum", next_state.get("sum", 0) + action.params["value"])
            return next_state

    wf = DummyWorkflow(name="dummy", num_stages=2)
    pathway = Pathway(
        actions=[
            Action(name="add", params={"value": 2}),
            Action(name="add", params={"value": 3}),
        ]
    )

    final_state = wf.rollout(sample_meta={"offset": 1}, pathway=pathway)

    assert final_state.get("sum") == 6
