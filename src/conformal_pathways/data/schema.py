from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Observation:
    """A declared observation; stage zero means available on entry."""

    value: Any
    source: str
    stage: int = 0

    def __post_init__(self):
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("observation source must be nonempty")
        if isinstance(self.stage, bool) or not isinstance(self.stage, int) or self.stage < 0:
            raise ValueError("observation stage must be a nonnegative integer")


@dataclass(frozen=True)
class PredictionInput:
    """Inference input: deliberately has no labels or arbitrary metadata."""

    sample_id: str
    dataset_source: str
    image_path: str | None
    observations: dict[str, Observation] = field(default_factory=dict)

    def observed_values(self, stage: int = 0) -> dict[str, Any]:
        return {k: deepcopy(v.value) for k, v in self.observations.items() if v.stage <= stage}


@dataclass
class Sample:
    sample_id: str
    dataset_source: str
    image_path: str | None
    labels: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    observations: dict[str, Observation] = field(default_factory=dict)

    def get_label(self, key: str, default: Any = None) -> Any:
        return self.labels.get(key, default)

    def has_label(self, key: str) -> bool:
        return key in self.labels and self.labels[key] is not None

    def group_id(self) -> str:
        # JSON encoding prevents delimiter collisions. Cross-source identity must
        # be supplied explicitly, rather than inferred from a local patient ID.
        if self.meta.get("global_patient_id") is not None:
            return json.dumps(["global_patient", str(self.meta["global_patient_id"])])
        for key in ("patient_id", "eye_id", "encounter_id"):
            value = self.meta.get(key)
            if value is not None and str(value).strip():
                return json.dumps([self.dataset_source, key, str(value)])
        return json.dumps([self.dataset_source, "sample_id", self.sample_id])

    def dme_label_available(self) -> bool:
        return isinstance(self.labels.get("dme_positive"), bool)

    def prediction_input(self) -> PredictionInput:
        self.validate()
        return PredictionInput(
            self.sample_id,
            self.dataset_source,
            self.image_path,
            {k: deepcopy(v) for k, v in self.observations.items() if v.stage == 0},
        )

    def observed_values(self) -> dict[str, Any]:
        return self.prediction_input().observed_values()

    def validate(self) -> None:
        for key in ("sample_id", "dataset_source"):
            value = getattr(self, key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key} must be a non-empty string")
        if self.image_path is not None and not isinstance(self.image_path, str):
            raise ValueError("image_path must be a string when provided")
        for key in ("labels", "meta", "observations"):
            if not isinstance(getattr(self, key), dict):
                raise ValueError(f"{key} must be a dict")
        for key, value in self.observations.items():
            if not isinstance(value, Observation):
                raise ValueError(f"{key}: observations must include source and stage")
        for key in ("patient_id", "eye_id", "encounter_id", "global_patient_id"):
            value = self.meta.get(key)
            if value is not None and (
                not str(value).strip() or isinstance(value, float) and not math.isfinite(value)
            ):
                raise ValueError(f"invalid {key}")


def validate_samples(samples: list[Sample]) -> None:
    seen = set()
    for sample in samples:
        sample.validate()
        if sample.sample_id in seen:
            raise ValueError("duplicate sample_id; namespace IDs before combining sources")
        seen.add(sample.sample_id)
