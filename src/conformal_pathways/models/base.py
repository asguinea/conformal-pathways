from __future__ import annotations

from abc import ABC, abstractmethod

from conformal_pathways.data import Sample


class Predictor(ABC):
    @abstractmethod
    def fit(self, train_samples: list[Sample]) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict_proba(self, samples: list[Sample]) -> list[dict[str, float]]:
        raise NotImplementedError

    def uncertainty(self, samples: list[Sample]) -> list[float]:
        distributions = self.predict_proba(samples)
        uncertainties: list[float] = []
        for distribution in distributions:
            max_prob = max(distribution.values()) if distribution else 0.0
            uncertainties.append(1.0 - max_prob)
        return uncertainties
