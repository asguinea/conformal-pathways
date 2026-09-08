from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Sample:
    sample_id: str
    dataset_source: str
    image_path: str | None
    labels: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def get_label(self, key: str, default: Any = None) -> Any:
        return self.labels.get(key, default)

    def has_label(self, key: str) -> bool:
        return key in self.labels

    def group_id(self) -> str:
        if "patient_id" in self.meta:
            return f"patient:{self.meta['patient_id']}"
        if "eye_id" in self.meta:
            return f"eye:{self.meta['eye_id']}"
        if "encounter_id" in self.meta:
            return f"encounter:{self.meta['encounter_id']}"
        return f"sample:{self.sample_id}"

    def dme_label_available(self) -> bool:
        return "dme_positive" in self.labels and isinstance(
            self.labels["dme_positive"], bool
        )

    def validate(self) -> None:
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise ValueError("sample_id must be a non-empty string")
        if not isinstance(self.dataset_source, str) or not self.dataset_source:
            raise ValueError("dataset_source must be a non-empty string")
        if self.image_path is not None and not isinstance(self.image_path, str):
            raise ValueError("image_path must be a string when provided")
        if not isinstance(self.labels, dict):
            raise ValueError("labels must be a dict")
