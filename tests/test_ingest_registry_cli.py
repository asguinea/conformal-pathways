from __future__ import annotations

from pathlib import Path

from conformal_pathways.ingest.base import DatasetBuilder
from conformal_pathways.ingest.registry import get_builder, list_builders, register_builder


class DummyBuilder(DatasetBuilder):
    name = "dummy_registry_test"

    def build_manifest(self, root: Path, out_csv: Path, **kwargs):
        return out_csv


def test_registry_register_and_lookup() -> None:
    builder = DummyBuilder()
    register_builder(builder)

    assert get_builder("dummy_registry_test") is builder
    assert "dummy_registry_test" in list_builders()
