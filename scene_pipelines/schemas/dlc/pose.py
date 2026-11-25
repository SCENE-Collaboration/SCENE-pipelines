"""DeepLabCut poses (Pose) and their optional links to a project and a video."""

import datajoint as dj

from scene_pipelines.core.access_markers import WriteRole, mark_write_role
from scene_pipelines.schemas.dlc._schema import schema
from scene_pipelines.schemas.dlc.project import DlcProject  # noqa: F401  # FK: PoseDlcProject
from scene_pipelines.schemas.files.files import File  # noqa: F401  # FK: Pose -> File
from scene_pipelines.schemas.video.video import VideoFile  # noqa: F401  # FK: PoseVideo


@mark_write_role(WriteRole.ACQUISITION)
@schema
class Pose(dj.Manual):
    """Keypoint positions over a recording; write with ``register_pose``."""

    definition = """
    pose_id: uuid  # from the file's SHA-256 when read from one
    ---
    -> [nullable] File  # the DeepLabCut output .h5 it was read from, if any
    scorer: varchar(255)  # model name in the .h5; DLC_live for DLC-live
    n_frames: int32
    frame_index=null: <blob>  # int64 (n_frames,): video frame of each pose; null = 0..n_frames-1
    frame_time=null: <blob>  # float64 (n_frames,): seconds of each pose; null = not recorded
    unique index (file_sha256)
    """

    class Keypoint(dj.Part):
        """One keypoint over all frames, in the source's column order."""

        definition = """
        -> master
        keypoint_index: int16
        ---
        bodypart: varchar(64)
        individual=null: varchar(64)  # null in single-animal files
        x: <blob>  # float32 (n_frames,), pixels
        y: <blob>  # float32 (n_frames,), pixels
        likelihood: <blob>  # float32 (n_frames,)
        unique index (pose_id, individual, bodypart)
        """


@mark_write_role(WriteRole.ACQUISITION)
@schema
class PoseDlcProject(dj.Manual):
    """The DeepLabCut project whose model made a pose."""

    definition = """
    -> Pose
    ---
    -> DlcProject
    """


@mark_write_role(WriteRole.ACQUISITION)
@schema
class PoseVideo(dj.Manual):
    """The video a pose was computed from."""

    definition = """
    -> Pose
    ---
    -> VideoFile.proj(video_sha256='file_sha256')
    """
