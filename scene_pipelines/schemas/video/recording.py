"""The videos recorded in a session (VideoRecording)."""

import datajoint as dj

from scene_pipelines.core.access_markers import WriteRole, mark_write_role
from scene_pipelines.schemas.scene.session import Session  # noqa: F401  # FK: VideoRecording
from scene_pipelines.schemas.video._schema import schema
from scene_pipelines.schemas.video.video import VideoFile  # noqa: F401  # FK: VideoRecording


@mark_write_role(WriteRole.ACQUISITION)
@schema
class VideoRecording(dj.Manual):
    """One video recorded in a session; write with ``register_video_recording``."""

    definition = """
    -> Session
    take: int16  # 1, 2, ... per session
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
