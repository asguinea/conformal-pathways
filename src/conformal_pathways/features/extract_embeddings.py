from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
from pathlib import Path

import numpy as np

from .cache import ids_path_for, input_identity, validate_embedding_cache, write_embedding_cache

DEFAULT_CACHE_DIR = Path("artifacts/embeddings")
DEFAULT_OUT_PATH = DEFAULT_CACHE_DIR / "embeddings.npy"
PRETRAINED_WEIGHTS = "IMAGENET1K_V2"


def _require_torch():
    try:
        import torch
    except ModuleNotFoundError as exc:
        raise ImportError("install conformal-pathways[imaging] for embedding extraction") from exc
    return torch


def get_device(prefer_mps=True):
    torch = _require_torch()
    if prefer_mps and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def make_resnet50_backbone(weights=PRETRAINED_WEIGHTS, random_seed=None):
    torch = _require_torch()
    from torchvision.models import ResNet50_Weights, resnet50

    if weights == "random":
        if isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0:
            raise ValueError("random baseline requires an explicit nonnegative integer random_seed")
        # Restore the caller's RNG state on exit.
        with torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(random_seed)
            model = resnet50(weights=None)
    else:
        if weights != PRETRAINED_WEIGHTS or random_seed is not None:
            raise ValueError(
                "choose explicit IMAGENET1K_V2 weights or the separately seeded random baseline"
            )
        # Loading failures propagate. Never substitute a different model silently.
        model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2, progress=False)
    model.fc = torch.nn.Identity()
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model


def _ids_path_for(path):
    return ids_path_for(path)


def extract_embeddings_from_manifest(
    manifest_csv,
    dataset_root,
    out_path=str(DEFAULT_OUT_PATH),
    batch_size=32,
    num_workers=0,
    prefer_mps=True,
    max_items=None,
    weights=PRETRAINED_WEIGHTS,
    random_seed=None,
    force_extract=False,
    device=None,
):
    torch = _require_torch()
    from torchvision.models import ResNet50_Weights

    from .image_dataset import ManifestImageDataset

    if (
        isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size < 1
        or num_workers < 0
    ):
        raise ValueError("invalid batch_size or num_workers")
    if weights not in {PRETRAINED_WEIGHTS, "random"}:
        raise ValueError(
            "weights must name IMAGENET1K_V2 or random; moving DEFAULT aliases are not accepted"
        )
    if weights == "random" and (
        isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0
    ):
        raise ValueError("random baseline requires an explicit random_seed")
    if weights != "random" and random_seed is not None:
        raise ValueError("random_seed is only valid for the random baseline")
    inputs = input_identity(manifest_csv, dataset_root, max_items)
    transform = ResNet50_Weights.IMAGENET1K_V2.transforms()
    target_device = str(device or get_device(prefer_mps))
    versions = {
        name: importlib.metadata.version(name)
        for name in ("torch", "torchvision", "pillow", "numpy")
    }
    request = {
        "architecture": "resnet50",
        "torch_threads": torch.get_num_threads(),
        "torch_interop_threads": torch.get_num_interop_threads(),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "weights": weights,
        "random_seed": random_seed,
        "transform": repr(transform),
        "inputs": inputs,
        "versions": versions,
        "device": target_device,
        "batch_size": batch_size,
        "num_workers": num_workers,
    }
    out = Path(out_path)
    if out.suffix != ".npy":
        raise ValueError("out_path must end in .npy")
    if out.exists() and not force_extract:
        array, ids, _ = validate_embedding_cache(out, expected_request=request)
        return {
            "n": len(ids),
            "dim": array.shape[1],
            "out_path": str(out),
            "device": target_device,
            "cache_reused": True,
        }
    dataset = ManifestImageDataset(
        manifest_csv, dataset_root, transform=transform, max_items=max_items
    )
    loader = torch.utils.data.DataLoader(
        dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    model = make_resnet50_backbone(weights, random_seed)
    digest = hashlib.sha256()
    for key, tensor in sorted(model.state_dict().items()):
        digest.update(key.encode())
        digest.update(tensor.cpu().contiguous().numpy().tobytes())
    model = model.to(target_device)
    arrays, ids = [], []
    with torch.inference_mode():
        for batch in loader:
            values = model(batch["image"].to(target_device)).cpu().numpy().astype(np.float32)
            arrays.append(values)
            ids.extend(batch["sample_id"])
    embeddings = np.concatenate(arrays)
    write_embedding_cache(
        out,
        embeddings,
        ids,
        {
            "kind": "resnet50_embeddings",
            "request": request,
            "model_state_sha256": digest.hexdigest(),
        },
    )
    return {
        "n": len(ids),
        "dim": embeddings.shape[1],
        "out_path": str(out),
        "device": target_device,
        "cache_reused": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract explicitly identified ResNet50 embeddings"
    )
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--dataset_root", required=True)
    parser.add_argument("--out_path", default=str(DEFAULT_OUT_PATH))
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--max_items", type=int)
    parser.add_argument(
        "--weights", choices=[PRETRAINED_WEIGHTS, "random"], default=PRETRAINED_WEIGHTS
    )
    parser.add_argument("--random_seed", type=int)
    parser.add_argument("--force_extract", action="store_true")
    parser.add_argument("--prefer_mps", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args(argv)
    print(extract_embeddings_from_manifest(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
