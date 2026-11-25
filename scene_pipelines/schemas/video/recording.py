"""Cameras of a lab (Camera) and the videos they record in a session (VideoRecording)."""

import datajoint as dj

from scene_pipelines.core.access_markers import WriteRole, mark_write_role
from scene_pipelines.schemas.scene.lab import Lab  # noqa: F401  # FK: Camera -> Lab
from scene_pipelines.schemas.scene.session import Session  # noqa: F401  # FK: VideoRecording
from scene_pipelines.schemas.video._schema import schema
from scene_pipelines.schemas.video.video import VideoFile  # noqa: F401  # FK: VideoRecording


@mark_write_role(WriteRole.ACQUISITION)
@schema
class Camera(dj.Manual):
    """A camera or view, known by a code within one lab."""

    definition = """
    -> Lab
    camera_code: varchar(32)  # lab code, e.g. top, side, cam0
    ---
    camera_details='': varchar(255)
    """


@mark_write_role(WriteRole.ACQUISITION)
@schema
class VideoRecording(dj.Manual):
    """One take of one camera in a session; write with ``register_video_recording``."""

    definition = """
    -> Session
    -> Camera
    take: int16  # 1, 2, ... per camera in start order
    ---
    -> VideoFile  # the recorded video
    start_time=null: datetime  # recorder clock
    unique index (file_sha256)
    """

    class FrameTimestamps(dj.Part):
        """Time of each frame, as the recorder wrote them."""

        definition = """
        -> master
        ---
        frame_timestamps: <blob>  # float64 (n_frames,), seconds
        """
