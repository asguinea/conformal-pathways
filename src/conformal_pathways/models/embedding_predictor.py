from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from conformal_pathways.data import Sample
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

        embeddings = np.load(self.embeddings_path)
        ids_path = Path(self.ids_path)
        ids = [line.strip() for line in ids_path.read_text(encoding="utf-8").splitlines() if line.strip()]

        if embeddings.ndim != 2:
            raise ValueError("embeddings array must be 2D")
        if embeddings.shape[0] != len(ids):
            raise ValueError(
                f"embeddings row count {embeddings.shape[0]} does not match ids count {len(ids)}"
            )

        self._embeddings = embeddings.astype(np.float32, copy=False)
        self._id_to_index = {sample_id: idx for idx, sample_id in enumerate(ids)}

    def fit(self, train_samples: list[Sample]) -> None:
        LogisticRegressionCls = self._require_sklearn()
        self._load_cache()
        assert self._embeddings is not None

        requested_ids = [sample.sample_id for sample in train_samples]
        X_rows: list[np.ndarray] = []
        y_labels: list[str] = []
        valid_class_values = {str(value) for value in self.class_values}

        for sample_id in requested_ids:
            if sample_id not in self._id_to_index:
                continue
            if sample_id not in self.label_map:
                continue

            label = str(self.label_map[sample_id])
            if label not in valid_class_values:
                continue

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
        self._model.fit(X, y)

    def predict_proba(self, samples: list[Sample]) -> list[dict[str, float]]:
        if self._model is None:
            raise ValueError("predictor must be fit before calling predict_proba")
        self._load_cache()
        assert self._embeddings is not None

        missing = [sample.sample_id for sample in samples if sample.sample_id not in self._id_to_index]
        if missing:
            raise KeyError(f"missing embeddings for sample_ids: {missing[:3]}")

        X = np.vstack([self._embeddings[self._id_to_index[sample.sample_id]] for sample in samples]).astype(
            np.float32
        )
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
    manifest_csv: str,
    dataset_root: str,
    embeddings_path: str,
    ids_path: str,
    label_key: str,
    class_values: list[Any],
) -> EmbeddingLogRegPredictor:
    del dataset_root
    df = pd.read_csv(manifest_csv)
    if "sample_id" not in df.columns:
        raise ValueError("manifest must contain sample_id column")
    if label_key not in df.columns:
        raise ValueError(f"manifest must contain label column '{label_key}'")

    label_map: dict[str, Any] = {}
    train_samples: list[Sample] = []
    for _, row in df.iterrows():
        sample_id = str(row["sample_id"])
        label = row[label_key]
        if pd.isna(label):
            continue
        label_map[sample_id] = label
        train_samples.append(
            Sample(
                sample_id=sample_id,
                dataset_source=str(row["dataset_source"]) if "dataset_source" in df.columns else "manifest",
                image_path=str(row["image_path"]) if "image_path" in df.columns else None,
                labels={label_key: label},
                meta={},
            )
        )

    predictor = EmbeddingLogRegPredictor(
        embeddings_path=embeddings_path,
        ids_path=ids_path,
        label_map=label_map,
        class_values=class_values,
    )
    predictor.fit(train_samples)
    return predictor
