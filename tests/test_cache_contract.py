import numpy as np
import pandas as pd
import pytest

from conformal_pathways.features.cache import (
    ids_path_for,
    input_identity,
    validate_embedding_cache,
    write_embedding_cache,
)


def test_embedding_integrity_and_requested_identity(tmp_path):
    out = tmp_path / "values.npy"
    request = {"weights": "explicit_test", "transform": "identity", "inputs": ["a", "b"]}
    write_embedding_cache(out, np.ones((2, 3)), ["a", "b"], {"kind": "test", "request": request})
    values, ids, meta = validate_embedding_cache(out, expected_request=request)
    assert values.shape == (2, 3) and ids == ["a", "b"]
    with pytest.raises(ValueError, match="provenance"):
        validate_embedding_cache(out, expected_request={**request, "weights": "different"})
    np.save(out, np.zeros((2, 3), dtype=np.float32))
    with pytest.raises(ValueError, match="hash"):
        validate_embedding_cache(out)


def test_missing_sidecar_and_duplicate_ids_fail(tmp_path):
    out = tmp_path / "values.npy"
    np.save(out, np.ones((2, 3)))
    ids_path_for(out).write_text("a\nb\n")
    with pytest.raises(ValueError, match="sidecar"):
        validate_embedding_cache(out)
    with pytest.raises(ValueError, match="unique"):
        write_embedding_cache(out, np.ones((2, 3)), ["a", "a"], {"kind": "test"})
    with pytest.raises(ValueError, match="finite"):
        write_embedding_cache(out, np.array([[np.nan]]), ["a"], {"kind": "test"})


def test_input_identity_hashes_images_and_preserves_ids(tmp_path):
    image = tmp_path / "image.bin"
    image.write_bytes(b"version-one")
    manifest = tmp_path / "inputs.csv"
    pd.DataFrame([{"sample_id": "001", "image_path": "image.bin"}]).to_csv(manifest, index=False)
    first = input_identity(manifest, tmp_path)
    image.write_bytes(b"version-two")
    second = input_identity(manifest, tmp_path)
    assert first[0]["sample_id"] == "001"
    assert first[0]["image_sha256"] != second[0]["image_sha256"]
    assert not first[0]["image_path"].startswith("/")


def test_id_file_tampering_is_detected(tmp_path):
    out = tmp_path / "values.npy"
    write_embedding_cache(out, np.ones((2, 2)), ["a", "b"], {"kind": "test"})
    ids_path_for(out).write_text("b\na\n")
    with pytest.raises(ValueError, match="hash"):
        validate_embedding_cache(out)


def test_weight_loading_failure_propagates_without_random_fallback(monkeypatch):
    pytest.importorskip("torch")
    models = pytest.importorskip("torchvision.models")
    from conformal_pathways.features.extract_embeddings import make_resnet50_backbone

    calls = []

    def fail(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("weights unavailable")

    monkeypatch.setattr(models, "resnet50", fail)
    with pytest.raises(RuntimeError, match="weights unavailable"):
        make_resnet50_backbone()
    assert len(calls) == 1
    assert calls[0]["weights"] == models.ResNet50_Weights.IMAGENET1K_V2
    with pytest.raises(ValueError, match="explicit"):
        make_resnet50_backbone(weights="random")
    assert len(calls) == 1


def test_embedding_model_fits_only_explicit_training_labels(tmp_path):
    pytest.importorskip("sklearn")
    from conformal_pathways.data import Sample
    from conformal_pathways.models import EmbeddingLogRegPredictor

    path = tmp_path / "values.npy"
    write_embedding_cache(
        path,
        np.array([[-2.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [2.0, 0.0]]),
        ["a", "b", "c", "d"],
        {"kind": "synthetic_test"},
    )
    training = [Sample("a", "s", None), Sample("d", "s", None)]
    outputs = []
    for hidden in ("low", "high"):
        model = EmbeddingLogRegPredictor(
            str(path),
            str(ids_path_for(path)),
            {"a": "low", "d": "high", "b": hidden, "c": hidden},
            ["low", "high"],
        )
        model.fit(training)
        assert set(model.label_map) == {"a", "d"}
        outputs.append(model.predict_proba([Sample("b", "s", None).prediction_input()]))
    assert outputs[0] == outputs[1]
    with pytest.raises(ValueError, match="missing training embedding"):
        model.fit([Sample("absent", "s", None)])


def test_random_image_extraction_repeats_and_rejects_stale_cache(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    Image = pytest.importorskip("PIL.Image")
    from conformal_pathways.features.extract_embeddings import extract_embeddings_from_manifest

    torch.set_num_threads(1)
    image = tmp_path / "image.png"
    Image.new("RGB", (32, 32), (20, 40, 60)).save(image)
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{"sample_id": "001", "image_path": image.name}]).to_csv(manifest, index=False)
    a, b = tmp_path / "a.npy", tmp_path / "b.npy"
    kwargs = dict(weights="random", random_seed=12, device="cpu", batch_size=1)
    first = extract_embeddings_from_manifest(str(manifest), str(tmp_path), str(a), **kwargs)
    repeat = extract_embeddings_from_manifest(str(manifest), str(tmp_path), str(b), **kwargs)
    np.testing.assert_array_equal(np.load(a), np.load(b))
    assert not first["cache_reused"] and not repeat["cache_reused"]
    assert extract_embeddings_from_manifest(str(manifest), str(tmp_path), str(a), **kwargs)[
        "cache_reused"
    ]
    with pytest.raises(ValueError, match="provenance"):
        extract_embeddings_from_manifest(
            str(manifest), str(tmp_path), str(a), **{**kwargs, "random_seed": 13}
        )
    Image.new("RGB", (32, 32), (60, 40, 20)).save(image)
    with pytest.raises(ValueError, match="provenance"):
        extract_embeddings_from_manifest(str(manifest), str(tmp_path), str(a), **kwargs)


def test_cache_sidecar_requires_provenance_even_for_external_embeddings(tmp_path):
    import json

    from conformal_pathways.features.cache import metadata_path_for

    out = tmp_path / "values.npy"
    write_embedding_cache(out, np.ones((1, 2)), ["a"], {"kind": "external_test"})
    sidecar = metadata_path_for(out)
    payload = json.loads(sidecar.read_text())
    del payload["provenance"]
    sidecar.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="provenance"):
        validate_embedding_cache(out)
