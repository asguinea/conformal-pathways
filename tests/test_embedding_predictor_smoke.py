from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sklearn")

from conformal_pathways.data import Sample
from conformal_pathways.models.embedding_predictor import EmbeddingLogRegPredictor


def test_embedding_logreg_predictor_smoke(tmp_path) -> None:
    rng = np.random.default_rng(0)
    sample_ids = ["s1", "s2", "s3", "s4"]
    embeddings = rng.normal(size=(4, 2048)).astype(np.float32)

    embeddings_path = tmp_path / "embeddings.npy"
    ids_path = tmp_path / "embeddings_ids.txt"
    np.save(embeddings_path, embeddings)
    ids_path.write_text("\n".join(sample_ids) + "\n", encoding="utf-8")

    label_map = {"s1": "neg", "s2": "neg", "s3": "pos", "s4": "pos"}
    class_values = ["neg", "pos"]

    predictor = EmbeddingLogRegPredictor(
        embeddings_path=str(embeddings_path),
        ids_path=str(ids_path),
        label_map=label_map,
        class_values=class_values,
    )
    train_samples = [
        Sample(sample_id=sid, dataset_source="synthetic", image_path=None, labels={}, meta={})
        for sid in sample_ids
    ]
    predictor.fit(train_samples)

    query_samples = train_samples[:3]
    probs = predictor.predict_proba(query_samples)
    uncertainties = predictor.uncertainty(query_samples)

    assert len(probs) == 3
    for dist in probs:
        assert set(dist.keys()) == {"neg", "pos"}
        assert abs(sum(dist.values()) - 1.0) < 1e-6

    assert len(uncertainties) == 3
    assert all(0.0 <= value <= 1.0 for value in uncertainties)
