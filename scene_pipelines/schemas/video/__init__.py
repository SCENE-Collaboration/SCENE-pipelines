"""SCENE shared video tables (VideoFile, VideoRecording, VideoTransform, ProcessedVideo).

DDL: ``VIDEO_SCHEMA_VERSION`` / ``SchemaVersion``.
"""

from scene_pipelines.schemas.video._schema import VIDEO_SCHEMA_VERSION

__all__ = ["VIDEO_SCHEMA_VERSION"]
