from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

from conformal_pathways.data import PredictionInput, Sample, validate_samples
from conformal_pathways.features.cache import validate_embedding_cache
from conformal_pathways.models.base import Predictor

try:
    from sklearn.linear_model import LogisticRegression
except ModuleNotFoundError:  # pragma: no cover - depends on environment
    LogisticRegression = None  # type: ignore[assignment]


class EmbeddingLogRegPredictor(Predictor):
    def __init__(
        self,
        embeddings_path: str,
        ids_path: str,
        label_map: dict[str, Any],
        class_values: list[Any],
        C: float = 1.0,
    ) -> None:
        if not class_values:
            raise ValueError("class_values must be non-empty")
        if len({str(v) for v in class_values}) != len(class_values):
            raise ValueError("class_values must have unique string representations")
        if not math.isfinite(C) or C <= 0:
            raise ValueError("C must be finite and positive")
        self.embeddings_path = embeddings_path
        self.ids_path = ids_path
        self.label_map = dict(label_map)
        self.class_values = list(class_values)
        self.C = C

        self._embeddings: np.ndarray | None = None
        self._id_to_index: dict[str, int] = {}
        self._model: Any = None

    def _require_sklearn(self) -> Any:
        if LogisticRegression is None:  # pragma: no cover - depends on environment
            raise ImportError("scikit-learn is required for EmbeddingLogRegPredictor")
        return LogisticRegression

    def _load_cache(self) -> None:
        if self._embeddings is not None and self._id_to_index:
            return

        embeddings, ids, self.cache_metadata = validate_embedding_cache(
            self.embeddings_path, self.ids_path
        )

        self._embeddings = embeddings.astype(np.float32, copy=False)
        self._id_to_index = {sample_id: idx for idx, sample_id in enumerate(ids)}

    def fit(self, train_samples: list[Sample]) -> None:
        validate_samples(train_samples)
        LogisticRegressionCls = self._require_sklearn()
        self._load_cache()
        assert self._embeddings is not None

        requested_ids = [sample.sample_id for sample in train_samples]
        X_rows: list[np.ndarray] = []
        y_labels: list[str] = []
        valid_class_values = {str(value) for value in self.class_values}

        for sample_id in requested_ids:
            if sample_id not in self._id_to_index:
                raise ValueError(f"missing training embedding: {sample_id}")
            if sample_id not in self.label_map:
                raise ValueError(f"missing training label: {sample_id}")

            label = str(self.label_map[sample_id])
            if label not in valid_class_values:
                raise ValueError(f"training label is outside class_values: {label}")

            X_rows.append(self._embeddings[self._id_to_index[sample_id]])
            y_labels.append(label)

        if not X_rows:
            raise ValueError("no train samples matched embeddings + label_map")
        if len(set(y_labels)) < 2:
            raise ValueError("logistic regression requires at least two classes in training data")

        X = np.vstack(X_rows).astype(np.float32)
        y = np.array(y_labels)

        self._model = LogisticRegressionCls(
            C=self.C,
            solver="lbfgs",
            max_iter=1000,
            random_state=0,
        )
        from sklearn.exceptions import ConvergenceWarning

        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            self._model.fit(X, y)
        self.training_ids = frozenset(requested_ids)
        self.training_groups = frozenset(s.group_id() for s in train_samples)
        self.label_map = {sid: self.label_map[sid] for sid in requested_ids}

    def predict_proba(self, samples: list[PredictionInput]) -> list[dict[str, float]]:
        if self._model is None:
            raise ValueError("predictor must be fit before calling predict_proba")
        self._load_cache()
        assert self._embeddings is not None

        missing = [
            sample.sample_id for sample in samples if sample.sample_id not in self._id_to_index
        ]
        if missing:
            raise KeyError(f"missing embeddings for sample_ids: {missing[:3]}")

        if not samples:
            return []
        X = np.vstack(
            [self._embeddings[self._id_to_index[sample.sample_id]] for sample in samples]
        ).astype(np.float32)
        proba = self._model.predict_proba(X)
        model_classes = [str(cls) for cls in self._model.classes_]
        class_order = [str(value) for value in self.class_values]

        outputs: list[dict[str, float]] = []
        for row in proba:
            dist = {class_name: 0.0 for class_name in class_order}
            for idx, class_name in enumerate(model_classes):
                dist[class_name] = float(row[idx])
            total = sum(dist.values())
            if total > 0:
                dist = {key: value / total for key, value in dist.items()}
            outputs.append(dist)

        return outputs

    def uncertainty(self, samples: list[Sample]) -> list[float]:
        distributions = self.predict_proba(samples)
        return [1.0 - max(dist.values()) for dist in distributions]


def train_embedding_logreg_from_manifest(
    manifest_csv, dataset_root, embeddings_path, ids_path, label_key, class_values, *, train_ids
):
    """Fit only explicitly listed training IDs; never infer training from a whole manifest."""
    from conformal_pathways.eval.run_with_embeddings import samples_from_manifest_csv

    samples = samples_from_manifest_csv(manifest_csv)
    lookup = {s.sample_id: s for s in samples}
    if len(train_ids) != len(set(train_ids)) or set(train_ids) - lookup.keys():
        raise ValueError("invalid explicit training IDs")
    train = [lookup[sid] for sid in train_ids]
    model = EmbeddingLogRegPredictor(
        embeddings_path,
        ids_path,
        {s.sample_id: s.get_label(label_key) for s in train},
        class_values,
    )
    model.fit(train)
    return model
