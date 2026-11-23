"""SCENE shared files: ``File`` (identity, by SHA-256) and ``FileContent`` (bytes in the store).

DDL: ``FILES_SCHEMA_VERSION`` / ``SchemaVersion``.
"""

from scene_pipelines.schemas.files._schema import FILES_SCHEMA_VERSION

__all__ = ["FILES_SCHEMA_VERSION"]
