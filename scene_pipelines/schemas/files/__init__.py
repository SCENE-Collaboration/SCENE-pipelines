"""SCENE shared files (``File``).

The bytes of recordings, videos and other files from outside the pipeline live in the
``scene-files`` store (a lab server, an S3 bucket), not in the database. ``File`` identifies
them by content and references them with DataJoint's ``<filepath@>`` type. What a file is
(a video, an EEG recording) belongs to the table that references ``File``.

DDL: ``FILES_SCHEMA_VERSION`` / ``SchemaVersion``.
"""

from scene_pipelines.schemas.files._schema import FILES_SCHEMA_VERSION

__all__ = ["FILES_SCHEMA_VERSION"]
