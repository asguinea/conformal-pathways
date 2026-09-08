from importlib import import_module

__all__ = ["ManifestImageDataset", "extract_embeddings_from_manifest"]


def __getattr__(name):
    modules = {
        "ManifestImageDataset": "image_dataset",
        "extract_embeddings_from_manifest": "extract_embeddings",
    }
    if name not in modules:
        raise AttributeError(name)
    value = getattr(import_module(f".{modules[name]}", __name__), name)
    globals()[name] = value
    return value
