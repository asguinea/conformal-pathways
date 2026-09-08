from __future__ import annotations

from conformal_pathways.ingest.base import DatasetBuilder, list_image_files, validate_manifest_df
from conformal_pathways.ingest.eyepacs import EyePACSBuilder
from conformal_pathways.ingest.idrid import IDRiDBuilder
from conformal_pathways.ingest.messidor2 import Messidor2Builder
from conformal_pathways.ingest.refuge import REFUGEBuilder
from conformal_pathways.ingest.registry import get_builder, list_builders, register_builder
from conformal_pathways.ingest.rimone import RIMONEBuilder


for builder in (
    EyePACSBuilder(),
    IDRiDBuilder(),
    Messidor2Builder(),
    REFUGEBuilder(),
    RIMONEBuilder(),
):
    register_builder(builder)


__all__ = [
    "DatasetBuilder",
    "validate_manifest_df",
    "list_image_files",
    "register_builder",
    "get_builder",
    "list_builders",
    "EyePACSBuilder",
    "IDRiDBuilder",
    "Messidor2Builder",
    "REFUGEBuilder",
    "RIMONEBuilder",
]
