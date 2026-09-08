from __future__ import annotations

from typing import Any

from conformal_pathways.data.loaders import normalize_glaucoma_risk

from .core import Action, DiagnosticResult, State, Workflow, validate_result


class GlaucomaWorkflow(Workflow):
    def __init__(self) -> None:
        super().__init__(name="glaucoma_workflow", num_stages=3)

    def initial_state(self, sample_meta: dict[str, Any]) -> State:
        risk = sample_meta.get("glaucoma_risk")
        risk = normalize_glaucoma_risk(risk) if risk is not None else None
        return State(
            observed={
                "glaucoma_risk": risk,
                "observation_history": [],
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
        sample_meta: DiagnosticResult | None,
    ) -> State:
        """Return a NEW State; do not mutate the input state."""
        self.validate_stage_index(stage)
        validate_result(sample_meta, stage, action)
        if sample_meta and action.name != "order_extra_tests":
            raise ValueError("only order_extra_tests can receive a diagnostic result")
        if action not in self.actions_at(stage, state):
            raise ValueError("action or parameters are not admissible at this stage")
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
                if sample_meta:
                    value = sample_meta.observation.value
                    if value not in {None, "low", "high"}:
                        raise ValueError("glaucoma proxy result must be low, high, or unavailable")
                    if value is not None:
                        next_state.set("glaucoma_risk", value)
                    next_state.set("diagnostic_result_unavailable", value is None)
                    next_state.set(
                        "observation_history",
                        [
                            *state.get("observation_history", []),
                            {
                                "name": "glaucoma_risk",
                                "value": value,
                                "stage": stage,
                                "source": sample_meta.observation.source,
                            },
                        ],
                    )
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
            raise ValueError(f"Unexpected action '{action.name}' at stage 3; expected: followup")
        if "weeks" not in action.params:
            raise ValueError("Action 'followup' at stage 3 requires a 'weeks' parameter")

        weeks = action.params["weeks"]
        allowed_weeks = {4, 12, 24}
        if weeks not in allowed_weeks:
            raise ValueError(
                f"Invalid followup weeks '{weeks}' at stage 3; expected one of: 4, 12, 24"
            )
        next_state.set("followup_weeks", weeks)
        return next_state
