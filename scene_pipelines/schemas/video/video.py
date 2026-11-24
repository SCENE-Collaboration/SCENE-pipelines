"""SCENE-shared videos (VideoFile)."""

import datajoint as dj

from scene_pipelines.core.access_markers import WriteRole, mark_write_role
from scene_pipelines.schemas.files.files import File  # noqa: F401  # FK: VideoFile -> File
from scene_pipelines.schemas.video._schema import schema


@mark_write_role(WriteRole.ACQUISITION)
@schema
class VideoFile(dj.Manual):
    """A video file and the metadata read from it; write with ``register_video``."""

    definition = """
    -> File
    ---
    fps: float64  # frames per second, as the container reports it
    width: int32  # pixels
    height: int32  # pixels
    n_frames: int32  # as OpenCV reports it; approximate for some codecs
    """
