"""Write and read helpers for the DeepLabCut tables; reading files needs ``[dlc]``."""

from scene_pipelines.ingestion.dlc._version import DLC_WRITER_VERSION
from scene_pipelines.ingestion.dlc.pose import register_pose
from scene_pipelines.ingestion.dlc.project import (
    dlc_project_key,
    register_dlc_project,
    register_project_config,
)
from scene_pipelines.ingestion.dlc.read import KeypointTrace, keypoint, pose_array, pose_dataframe

__all__ = [
    "DLC_WRITER_VERSION",
    "KeypointTrace",
    "dlc_project_key",
    "keypoint",
    "pose_array",
    "pose_dataframe",
    "register_dlc_project",
    "register_pose",
    "register_project_config",
]
