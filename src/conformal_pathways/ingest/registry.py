from __future__ import annotations

from conformal_pathways.ingest.base import DatasetBuilder


_BUILDERS: dict[str, DatasetBuilder] = {}


def register_builder(builder: DatasetBuilder) -> None:
    if not builder.name:
        raise ValueError("builder name must be non-empty")
    _BUILDERS[builder.name] = builder


def get_builder(name: str) -> DatasetBuilder:
    if name not in _BUILDERS:
        raise KeyError(f"unknown dataset builder: {name}")
    return _BUILDERS[name]


def list_builders() -> list[str]:
    return sorted(_BUILDERS)
