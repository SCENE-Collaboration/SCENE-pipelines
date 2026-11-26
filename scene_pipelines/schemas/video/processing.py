"""A lab's video processing recipes (VideoTransform) and the videos they make (ProcessedVideo)."""

import datajoint as dj

from scene_pipelines.core.access_markers import WriteRole, mark_write_role
from scene_pipelines.schemas.scene.lab import Lab  # noqa: F401  # FK: VideoTransform -> Lab
from scene_pipelines.schemas.video._schema import schema
from scene_pipelines.schemas.video.recording import VideoRecording  # noqa: F401  # FK
from scene_pipelines.schemas.video.video import VideoFile  # noqa: F401  # FK: ProcessedVideo


@mark_write_role(WriteRole.ACQUISITION)
@schema
class VideoTransform(dj.Manual):
    """A lab's named recipe for processing videos; write with ``ensure_video_transform``."""

    definition = """
    -> Lab
    transform_code: varchar(64)  # lab code, e.g. crop-arena, undistort
    ---
    transform_name='': varchar(255)
    transform_steps=null: json  # the lab's description of the steps; SCENE does not read it
    """


@mark_write_role(WriteRole.ACQUISITION)
@schema
class ProcessedVideo(dj.Manual):
    """A video made from a recording by a transform of the session's lab.

    Write with ``register_processed_video``, which checks the lab.
    """

    definition = """
    -> VideoRecording
    -> VideoTransform
    ---
    -> VideoFile  # the processed video
    unique index (file_sha256)
    """
