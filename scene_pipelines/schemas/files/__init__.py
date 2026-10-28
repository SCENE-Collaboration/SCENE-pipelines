"""SCENE shared file catalogue (Store, File, Location).

The bytes of recordings, videos and large analysis files live in stores
(lab servers, S3 buckets), not in the database. ``File`` identifies bytes by content;
``Location`` lists the stores that hold a copy now, at ``object_key(file_sha256)``.
What a file is (a video, a labels file) belongs to the table that references ``File``.

DDL: ``FILES_SCHEMA_VERSION`` / ``SchemaVersion``.
"""

from scene_pipelines.schemas.files._schema import FILES_SCHEMA_VERSION

__all__ = ["FILES_SCHEMA_VERSION"]
