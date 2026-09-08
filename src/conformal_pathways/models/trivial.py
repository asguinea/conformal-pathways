from __future__ import annotations

import math
from typing import Any

from conformal_pathways.data import PredictionInput, Sample, validate_samples
from conformal_pathways.models.base import Predictor


class TrivialLabelPredictor(Predictor):
    def __init__(
        self,
        label_key: str,
        class_values: list[Any],
        smoothing: float = 1e-3,
    ) -> None:
        if not class_values:
            raise ValueError("class_values must be non-empty")
        if not math.isfinite(smoothing) or smoothing <= 0:
            raise ValueError("smoothing must be > 0")

        if len({str(v) for v in class_values}) != len(class_values):
            raise ValueError("duplicate class values")
        self.label_key = label_key
        self.class_values = list(class_values)
        self.smoothing = smoothing
        self._prior_by_class: dict[str, float] = {}

    def fit(self, train_samples: list[Sample]) -> None:
        validate_samples(train_samples)
        if not any(s.has_label(self.label_key) for s in train_samples):
            raise ValueError("no observed training labels")
        self.training_ids = frozenset(s.sample_id for s in train_samples)
        self.training_groups = frozenset(s.group_id() for s in train_samples)
        counts: dict[Any, float] = {
            class_value: self.smoothing for class_value in self.class_values
        }

        for sample in train_samples:
            if sample.has_label(self.label_key):
                value = sample.get_label(self.label_key)
                if value in counts:
                    counts[value] += 1.0
                else:
                    raise ValueError("training label is outside class_values")

        total = sum(counts.values())
        self._prior_by_class = {
            str(class_value): counts[class_value] / total for class_value in self.class_values
        }

    def predict_proba(self, samples: list[PredictionInput]) -> list[dict[str, float]]:
        if not self._prior_by_class:
            raise ValueError("predictor must be fit before calling predict_proba")

        return [dict(self._prior_by_class) for _ in samples]
