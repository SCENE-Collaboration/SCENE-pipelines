"""Write helpers for the video tables; reading a video needs ``scene-pipelines[video]``."""

from scene_pipelines.ingestion.video._version import VIDEO_WRITER_VERSION
from scene_pipelines.ingestion.video.recording import register_video_recording
from scene_pipelines.ingestion.video.video import register_video

__all__ = ["VIDEO_WRITER_VERSION", "register_video", "register_video_recording"]
