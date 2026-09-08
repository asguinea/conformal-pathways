from __future__ import annotations

from typing import Any

from .core import Action, State, Workflow


class GlaucomaWorkflow(Workflow):
    def __init__(self) -> None:
        super().__init__(name="glaucoma_workflow", num_stages=3)

    def initial_state(self, sample_meta: dict[str, Any]) -> State:
        return State(
            observed={
                "glaucoma_risk": sample_meta.get("glaucoma_risk"),
                "tests_ordered": [],
                "management": None,
                "followup_weeks": None,
            }
        )

    def actions_at(self, stage: int, state: State) -> list[Action]:
        self.validate_stage_index(stage)
        if stage == 1:
            return [Action("order_extra_tests"), Action("no_extra_tests")]
        if stage == 2:
            return [
                Action("treat"),
                Action("refer_glaucoma"),
                Action("monitor"),
            ]
        return [
            Action("followup", {"weeks": 4}),
            Action("followup", {"weeks": 12}),
            Action("followup", {"weeks": 24}),
        ]

    def transition(
        self,
        stage: int,
        state: State,
        action: Action,
        sample_meta: dict[str, Any],
    ) -> State:
        """Return a NEW State; do not mutate the input state."""
        self.validate_stage_index(stage)
        next_state = state.copy()

        if stage == 1:
            allowed = {"order_extra_tests", "no_extra_tests"}
            if action.name not in allowed:
                raise ValueError(
                    f"Unexpected action '{action.name}' at stage 1; "
                    "expected one of: order_extra_tests, no_extra_tests"
                )
            if action.name == "order_extra_tests":
                next_state.set("tests_ordered", ["OCT_RNFL", "VF"])
            else:
                next_state.set("tests_ordered", [])
            return next_state

        if stage == 2:
            allowed = {"treat", "refer_glaucoma", "monitor"}
            if action.name not in allowed:
                raise ValueError(
                    f"Unexpected action '{action.name}' at stage 2; "
                    "expected one of: treat, refer_glaucoma, monitor"
                )
            next_state.set("management", action.name)
            return next_state

        if action.name != "followup":
            raise ValueError(
                f"Unexpected action '{action.name}' at stage 3; expected: followup"
            )
        if "weeks" not in action.params:
            raise ValueError(
                "Action 'followup' at stage 3 requires a 'weeks' parameter"
            )

        weeks = action.params["weeks"]
        allowed_weeks = {4, 12, 24}
        if weeks not in allowed_weeks:
            raise ValueError(
                f"Invalid followup weeks '{weeks}' at stage 3; expected one of: 4, 12, 24"
            )
        next_state.set("followup_weeks", weeks)
        return next_state
