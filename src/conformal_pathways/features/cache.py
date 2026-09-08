"""Content-addressed identities for embedding caches; no optional image imports."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

CACHE_SCHEMA = 1


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ids_path_for(path):
    path = Path(path)
    return path.with_name(f"{path.stem}_ids.txt")


def metadata_path_for(path):
    return Path(path).with_suffix(".metadata.json")


def input_identity(manifest_csv, dataset_root, max_items=None):
    frame = pd.read_csv(manifest_csv, dtype=str, keep_default_na=False)
    if not {"sample_id", "image_path"} <= set(frame):
        raise ValueError("manifest needs sample_id and image_path")
    if max_items is not None:
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        frame = frame.head(max_items)
    root = Path(dataset_root).resolve()
    records = []
    seen = set()
    for row in frame.to_dict("records"):
        sid = row["sample_id"]
        if not sid.strip() or sid in seen:
            raise ValueError("blank or duplicate embedding sample ID")
        seen.add(sid)
        if not row["image_path"].strip():
            raise ValueError("missing image_path")
        path = (root / row["image_path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("image path lies outside dataset_root")
        records.append(
            {
                "sample_id": sid,
                "dataset_source": row.get("dataset_source", ""),
                "image_path": str(path.relative_to(root)),
                "image_sha256": sha256_file(path),
            }
        )
    if not records:
        raise ValueError("empty embedding input manifest")
    return records


def write_embedding_cache(out_path, embeddings, sample_ids, provenance):
    out = Path(out_path)
    if out.suffix != ".npy":
        raise ValueError("embedding output must have .npy suffix")
    array = np.asarray(embeddings, dtype=np.float32)
    if (
        array.ndim != 2
        or min(array.shape) < 1
        or array.shape[0] != len(sample_ids)
        or not np.isfinite(array).all()
    ):
        raise ValueError("embeddings must be a nonempty finite matrix matching IDs")
    if len(set(sample_ids)) != len(sample_ids) or any(
        not isinstance(s, str) or not s.strip() or "\n" in s or "\r" in s for s in sample_ids
    ):
        raise ValueError("embedding IDs must be unique nonempty lines")
    if not isinstance(provenance, dict) or not provenance.get("kind"):
        raise ValueError("explicit embedding provenance kind is required")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=".embedding-write-") as temporary:
        temp = Path(temporary)
        matrix, ids, meta = temp / "values.npy", temp / "ids.txt", temp / "metadata.json"
        np.save(matrix, array, allow_pickle=False)
        ids.write_text("\n".join(sample_ids) + "\n")
        payload = {
            "schema_version": CACHE_SCHEMA,
            "shape": list(array.shape),
            "dtype": "float32",
            "embeddings_sha256": sha256_file(matrix),
            "ids_sha256": sha256_file(ids),
            "provenance": provenance,
        }
        meta.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        os.replace(matrix, out)
        os.replace(ids, ids_path_for(out))
        # Commit metadata last; any interrupted write is detected on next read.
        os.replace(meta, metadata_path_for(out))
    return payload


def validate_embedding_cache(out_path, ids_path=None, expected_request=None):
    out = Path(out_path)
    ids_file = Path(ids_path) if ids_path else ids_path_for(out)
    meta_file = metadata_path_for(out)
    if not meta_file.is_file():
        raise ValueError(
            "embedding cache has no provenance sidecar; regenerate or explicitly register external embeddings"
        )
    meta = json.loads(meta_file.read_text())
    if not isinstance(meta.get("provenance"), dict) or not meta["provenance"].get("kind"):
        raise ValueError("embedding cache provenance is missing")
    if meta.get("schema_version") != CACHE_SCHEMA:
        raise ValueError("unsupported embedding cache schema")
    if sha256_file(out) != meta.get("embeddings_sha256") or sha256_file(ids_file) != meta.get(
        "ids_sha256"
    ):
        raise ValueError("embedding cache content hash mismatch")
    ids = ids_file.read_text().splitlines()
    array = np.load(out, allow_pickle=False)
    if (
        array.ndim != 2
        or min(array.shape) < 1
        or list(array.shape) != meta.get("shape")
        or array.shape[0] != len(ids)
        or len(set(ids)) != len(ids)
        or not all(s.strip() for s in ids)
    ):
        raise ValueError("embedding cache shape or IDs are invalid")
    if str(array.dtype) != meta.get("dtype") or not np.isfinite(array).all():
        raise ValueError("embedding cache dtype or values are invalid")
    if (
        expected_request is not None
        and meta.get("provenance", {}).get("request") != expected_request
    ):
        raise ValueError(
            "embedding cache provenance does not match requested inputs, weights, transforms, or environment; use force_extract to regenerate"
        )
    return array, ids, meta
