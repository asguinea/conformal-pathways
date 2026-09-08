from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from conformal_pathways.features.image_dataset import ManifestImageDataset


DEFAULT_CACHE_DIR = Path("artifacts/embeddings")
DEFAULT_OUT_PATH = DEFAULT_CACHE_DIR / "embeddings.npy"


def _require_torch():
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
        raise ImportError("torch is required for embedding extraction") from exc
    return torch


def get_device(prefer_mps: bool = True):
    torch = _require_torch()
    if prefer_mps and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def make_resnet50_backbone():
    torch = _require_torch()
    try:
        from torchvision.models import ResNet50_Weights, resnet50
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
        raise ImportError("torchvision is required for ResNet50 backbone") from exc

    try:
        model = resnet50(weights=ResNet50_Weights.DEFAULT)
    except Exception as exc:  # pragma: no cover - network/cache dependent
        warnings.warn(
            f"Falling back to randomly initialized ResNet50 due to weight load failure: {exc}",
            stacklevel=2,
        )
        model = resnet50(weights=None)

    model.fc = torch.nn.Identity()
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    return model


def _ids_path_for(out_path: Path) -> Path:
    if out_path.suffix == ".npy":
        return out_path.with_name(f"{out_path.stem}_ids.txt")
    return out_path.with_name(f"{out_path.name}_ids.txt")


def extract_embeddings_from_manifest(
    manifest_csv: str,
    dataset_root: str,
    out_path: str = str(DEFAULT_OUT_PATH),
    batch_size: int = 32,
    num_workers: int = 0,
    prefer_mps: bool = True,
    max_items: int | None = None,
) -> dict[str, Any]:
    torch = _require_torch()

    out_path_obj = Path(out_path)
    if not out_path_obj.is_absolute() and out_path_obj.parent == Path("."):
        out_path_obj = DEFAULT_CACHE_DIR / out_path_obj.name
    out_path_obj.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    dataset = ManifestImageDataset(
        manifest_csv=manifest_csv,
        dataset_root=dataset_root,
        max_items=max_items,
    )
    dataloader = torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    device = get_device(prefer_mps=prefer_mps)
    model = make_resnet50_backbone().to(device)

    sample_ids: list[str] = []
    embedding_batches: list[np.ndarray] = []

    with torch.no_grad():
        for batch in dataloader:
            images = batch["image"].to(device)
            outputs = model(images)
            outputs_np = outputs.detach().cpu().float().numpy()
            embedding_batches.append(outputs_np)
            sample_ids.extend([str(sample_id) for sample_id in batch["sample_id"]])

    if embedding_batches:
        embeddings = np.concatenate(embedding_batches, axis=0).astype(np.float32)
    else:
        embeddings = np.empty((0, 2048), dtype=np.float32)

    np.save(out_path_obj, embeddings)

    ids_path = _ids_path_for(out_path_obj)
    with ids_path.open("w", encoding="utf-8") as f:
        for sample_id in sample_ids:
            f.write(f"{sample_id}\n")

    dim = int(embeddings.shape[1]) if embeddings.ndim == 2 and embeddings.shape[0] > 0 else 2048
    return {
        "n": int(embeddings.shape[0]),
        "dim": dim,
        "out_path": str(out_path_obj),
        "device": str(device),
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract ResNet50 embeddings from a manifest")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--dataset_root", required=True)
    parser.add_argument("--out_path", default=str(DEFAULT_OUT_PATH))
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--max_items", type=int, default=None)
    parser.add_argument(
        "--prefer_mps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prefer MPS if available (use --no-prefer_mps to disable)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    stats = extract_embeddings_from_manifest(
        manifest_csv=args.manifest_csv,
        dataset_root=args.dataset_root,
        out_path=args.out_path,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        prefer_mps=args.prefer_mps,
        max_items=args.max_items,
    )
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
