from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from conformal_pathways.data.schema import Observation


@dataclass(frozen=True)
class DiagnosticResult:
    """Result supplied after a diagnostic action has actually been executed."""

    action_name: str
    observation: Observation


def validate_result(result, stage: int, action: "Action") -> None:
    if result is None or result == {}:
        return
    if not isinstance(result, DiagnosticResult):
        raise TypeError("diagnostic results require DiagnosticResult, not a latent-label mapping")
    if result.action_name != action.name or result.observation.stage != stage:
        raise ValueError("diagnostic result does not match the executed action and stage")


def _freeze(obj: Any) -> Any:
    if isinstance(obj, dict):
        return tuple(sorted((key, _freeze(value)) for key, value in obj.items()))
    if isinstance(obj, (list, tuple)):
        return tuple(_freeze(item) for item in obj)
    if isinstance(obj, set):
        return tuple(sorted((_freeze(item) for item in obj), key=repr))
    if isinstance(obj, (str, bytes, int, float, bool, type(None))):
        return obj
    return repr(obj)


@dataclass(eq=False)
class Action:
    name: str
    params: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.name, _freeze(self.params)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Action):
            return False
        return (self.name, _freeze(self.params)) == (
            other.name,
            _freeze(other.params),
        )


@dataclass
class State:
    observed: dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "State":
        return State(observed=deepcopy(self.observed))

    def get(self, key: str, default: Any = None) -> Any:
        return self.observed.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.observed[key] = value


@dataclass
class Pathway:
    actions: list[Action] = field(default_factory=list)

    def append(self, action: Action) -> "Pathway":
        return Pathway(actions=[*self.actions, action])

    def __len__(self) -> int:
        return len(self.actions)

    def to_names(self) -> list[str]:
        return [action.name for action in self.actions]


class Workflow(ABC):
    name: str
    num_stages: int

    def __init__(self, name: str, num_stages: int) -> None:
        self.name = name
        self.num_stages = num_stages

    @abstractmethod
    def initial_state(self, sample_meta: dict[str, Any]) -> State:
        raise NotImplementedError

    @abstractmethod
    def actions_at(self, stage: int, state: State) -> list[Action]:
        raise NotImplementedError

    @abstractmethod
    def transition(
        self,
        stage: int,
        state: State,
        action: Action,
        sample_meta: DiagnosticResult | None,
    ) -> State:
        """Return a NEW State; do not mutate the input state."""
        raise NotImplementedError

    def validate_stage_index(self, stage: int) -> None:
        if (
            isinstance(stage, bool)
            or not isinstance(stage, int)
            or stage < 1
            or stage > self.num_stages
        ):
            raise ValueError(f"stage must be in [1, {self.num_stages}], got {stage}")

    def rollout(
        self,
        sample_meta: dict[str, Any],
        pathway: Pathway,
        diagnostic_results: dict[int, DiagnosticResult] | None = None,
    ) -> State:
        state = self.initial_state(sample_meta)
        for stage, action in enumerate(pathway.actions, start=1):
            self.validate_stage_index(stage)
            state = self.transition(stage, state, action, (diagnostic_results or {}).get(stage))
        return state
