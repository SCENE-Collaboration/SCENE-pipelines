"""SCENE shared DeepLabCut tables (DlcProject, ProjectConfig, Pose).

DDL: ``DLC_SCHEMA_VERSION`` / ``SchemaVersion``.
"""

from scene_pipelines.schemas.dlc._schema import DLC_SCHEMA_VERSION

__all__ = ["DLC_SCHEMA_VERSION"]
