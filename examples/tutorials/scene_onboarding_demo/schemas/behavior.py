"""The Demo lab's behaviour tables: its tracked recordings, and what is computed from them.

``Recording`` refers to shared rows: the session's video (``VideoRecording``), the DeepLabCut poses
of that video (``Pose``) and the project config with the likelihood threshold
(``ProjectConfig``). It adds what only the lab knows: the arena and where it is in the image.
``ingest`` fills it from a session folder's ``recording.json``; ``populate()`` fills the rest.

    Session ─> VideoRecording ─┐
    dlc.Pose ──────────────────┼──> Recording ──> Trajectory ──> Kinematics
    dlc.ProjectConfig, Arena ──┘
"""

from __future__ import annotations

import cv2
import datajoint as dj
import numpy as np
import pandas as pd
from scene_pipelines.core import SCENE_REGISTRY
from scene_pipelines.ingestion.dlc import keypoint
from scene_pipelines.schemas.dlc.pose import Pose
from scene_pipelines.schemas.dlc.project import ProjectConfig
from scene_pipelines.schemas.video.recording import VideoRecording  # noqa: F401  # FK
from scene_pipelines.schemas.video.video import VideoFile

schema = SCENE_REGISTRY.make_schema("behavior")

BODY_POINT = "mouse_center"  # the keypoint a Trajectory follows
MOVING_CM_S = 5.0  # faster than this counts as moving (locomotion, not the body point's wobble)
SMOOTHING_S = 0.2  # rolling-median window on positions
MAX_GAP_S = 0.2  # gaps below pcutoff up to this long are interpolated


@schema
class Arena(dj.Lookup):
    definition = """
    arena_name: varchar(32)
    ---
    width_cm: float32
    depth_cm: float32
    """


@schema
class Recording(dj.Manual):
    definition = """
    # a tracked video of a session, with its arena; from recording.json
    -> VideoRecording
    ---
    -> Pose                                              # the poses the lab analyses
    -> ProjectConfig.proj(config_sha256='file_sha256')   # the DeepLabCut config: its pcutoff
    -> Arena
    corners_px: <blob>                   # (4, 2) arena floor corners, clockwise from top-left
    video_path: varchar(1024)            # relative to the data folder; not uploaded
    """

    def pose(self, key) -> dict:
        """The ``Pose`` key of a recording."""
        return {"pose_id": (self & key).fetch1("pose_id")}

    def pcutoff(self, key) -> float:
        """The likelihood threshold of the config that tracked the recording."""
        config = ProjectConfig.proj("pcutoff", config_sha256="file_sha256")
        recording = (self & key).proj("dlc_project_id", "config_sha256")
        return float((recording * config).fetch1("pcutoff"))

    def times(self, key) -> np.ndarray:
        """Seconds of each pose from the first: DLC-live's times, else frame number / fps."""
        n_frames, frame_time = (Pose & self.pose(key)).fetch1("n_frames", "frame_time")
        if frame_time is not None:
            return frame_time - frame_time[0]
        fps = (VideoRecording * VideoFile & key).fetch1("fps")
        return np.arange(n_frames) / fps

    def pixels_to_cm(self, key) -> np.ndarray:
        """The (3, 3) perspective transform from image pixels to arena centimetres."""
        corners, width, depth = (self * Arena & key).fetch1("corners_px", "width_cm", "depth_cm")
        arena = np.float32([[0, 0], [width, 0], [width, depth], [0, depth]])
        return cv2.getPerspectiveTransform(np.float32(corners), arena)


@schema
class Trajectory(dj.Computed):
    definition = """
    # the body point's path in arena centimetres; poses below pcutoff dropped, short gaps filled
    -> Recording
    ---
    bodypart: varchar(64)
    x_cm: <blob>                         # NaN where untracked
    y_cm: <blob>
    speed_cm_s: <blob>
    """

    def make(self, key):
        recording = Recording()
        t = recording.times(key)
        x, y, likelihood = keypoint(recording.pose(key), BODY_POINT)
        pixels = np.column_stack([x, y]).astype(np.float32)
        cm = cv2.perspectiveTransform(pixels[None], recording.pixels_to_cm(key))[0].astype(float)
        cm[likelihood < recording.pcutoff(key)] = np.nan

        step = np.median(np.diff(t))
        track = pd.DataFrame(cm, columns=["x", "y"])
        track = track.interpolate(limit=round(MAX_GAP_S / step), limit_area="inside")
        window = max(1, round(SMOOTHING_S / step)) | 1
        track = track.rolling(window, center=True, min_periods=1).median()
        speed = np.hypot(np.gradient(track["x"], t), np.gradient(track["y"], t))
        self.insert1(
            {
                **key,
                "bodypart": BODY_POINT,
                "x_cm": track["x"].to_numpy(),
                "y_cm": track["y"].to_numpy(),
                "speed_cm_s": speed,
            }
        )


@schema
class Kinematics(dj.Computed):
    definition = """
    # summary of a trajectory
    -> Trajectory
    ---
    duration_s: float32
    distance_cm: float32
    mean_speed_cm_s: float32             # over tracked frames
    moving_fraction: float32             # of tracked frames, faster than MOVING_CM_S
    center_fraction: float32             # of tracked frames, in the central quarter of the arena
    """

    def make(self, key):
        t = Recording().times(key)
        x, y, speed = (Trajectory & key).fetch1("x_cm", "y_cm", "speed_cm_s")
        width, depth = (Recording * Arena & key).fetch1("width_cm", "depth_cm")
        tracked = ~np.isnan(x)
        central = (np.abs(x - width / 2) < width / 4) & (np.abs(y - depth / 2) < depth / 4)
        self.insert1(
            {
                **key,
                "duration_s": float(t[-1] - t[0]),
                "distance_cm": float(np.nansum(np.hypot(np.diff(x), np.diff(y)))),
                "mean_speed_cm_s": float(np.nanmean(speed)),
                "moving_fraction": float(np.mean(speed[tracked] > MOVING_CM_S)),
                "center_fraction": float(np.mean(central[tracked])),
            }
        )
