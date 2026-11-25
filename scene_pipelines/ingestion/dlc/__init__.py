"""Write helpers for the DeepLabCut tables; reading files needs ``[dlc]``.

Read stored poses back with ``scene_pipelines.query.dlc``.
"""

from scene_pipelines.ingestion.dlc._version import DLC_WRITER_VERSION
from scene_pipelines.ingestion.dlc.pose import register_pose
from scene_pipelines.ingestion.dlc.project import (
    dlc_project_key,
    register_dlc_project,
    register_project_config,
)

__all__ = [
    "DLC_WRITER_VERSION",
    "dlc_project_key",
    "register_dlc_project",
    "register_pose",
    "register_project_config",
]
