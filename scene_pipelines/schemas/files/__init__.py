"""SCENE shared files (``File``): bytes in the ``scene-files`` store, referenced by content.

DDL: ``FILES_SCHEMA_VERSION`` / ``SchemaVersion``.
"""

from scene_pipelines.schemas.files._schema import FILES_SCHEMA_VERSION

__all__ = ["FILES_SCHEMA_VERSION"]
