"""Write helpers for the video tables; reading a video needs ``scene-pipelines[video]``."""

from scene_pipelines.ingestion.video._version import VIDEO_WRITER_VERSION
from scene_pipelines.ingestion.video.processing import (
    ensure_video_transform,
    register_processed_video,
)
from scene_pipelines.ingestion.video.recording import ensure_camera, register_video_recording
from scene_pipelines.ingestion.video.video import register_video

__all__ = [
    "VIDEO_WRITER_VERSION",
    "ensure_camera",
    "ensure_video_transform",
    "register_processed_video",
    "register_video",
    "register_video_recording",
]
