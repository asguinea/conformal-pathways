from __future__ import annotations

from typing import Any

from .core import Action, State, Workflow


DME_STATUS_UNKNOWN = "unknown"
DME_STATUS_REVEALED_NEGATIVE = "revealed_negative"
DME_STATUS_REVEALED_POSITIVE = "revealed_positive"

# DR severity buckets are metadata-only for now; any string/int value is accepted.
DR_SEVERITY_ALLOWED_TYPES = (str, int)


class DRWorkflow(Workflow):
    def __init__(self) -> None:
        super().__init__(name="dr_workflow", num_stages=3)

    def initial_state(self, sample_meta: dict[str, Any]) -> State:
        return State(
            observed={
                "dr_severity": sample_meta.get("dr_severity"),
                "dme_status": DME_STATUS_UNKNOWN,
                "oct_ordered": False,
                "management": None,
                "followup_weeks": None,
            }
        )

    def actions_at(self, stage: int, state: State) -> list[Action]:
        self.validate_stage_index(stage)
        if stage == 1:
            return [Action("order_OCT"), Action("no_OCT")]
        if stage == 2:
            return [
                Action("refer_retina"),
                Action("anti_VEGF"),
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
            allowed = {"order_OCT", "no_OCT"}
            if action.name not in allowed:
                raise ValueError(
                    f"Unexpected action '{action.name}' at stage 1; "
                    "expected one of: order_OCT, no_OCT"
                )
            if action.name == "order_OCT":
                next_state.set("oct_ordered", True)
                has_labels = sample_meta.get("dme_label_available") is True
                dme_positive = sample_meta.get("dme_positive")
                if has_labels and isinstance(dme_positive, bool):
                    if dme_positive:
                        next_state.set("dme_status", DME_STATUS_REVEALED_POSITIVE)
                    else:
                        next_state.set("dme_status", DME_STATUS_REVEALED_NEGATIVE)
            return next_state

        if stage == 2:
            allowed = {"refer_retina", "anti_VEGF", "monitor"}
            if action.name not in allowed:
                raise ValueError(
                    f"Unexpected action '{action.name}' at stage 2; "
                    "expected one of: refer_retina, anti_VEGF, monitor"
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
