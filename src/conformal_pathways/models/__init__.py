from importlib import import_module

from .base import Predictor
from .trivial import TrivialLabelPredictor

__all__ = [
    "EmbeddingLogRegPredictor",
    "Predictor",
    "TrivialLabelPredictor",
    "train_embedding_logreg_from_manifest",
]


def __getattr__(name: str):
    if name not in {"EmbeddingLogRegPredictor", "train_embedding_logreg_from_manifest"}:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".embedding_predictor", __name__), name)
    globals()[name] = value
    return value
