"""Row-level write provenance for the DeepLabCut tables."""

from scene_pipelines.schemas.dlc._schema import schema
from scene_pipelines.schemas.dlc.pose import Pose, PoseDlcProject, PoseVideo
from scene_pipelines.schemas.dlc.project import DlcProject, ProjectConfig
from scene_pipelines.schemas.provenance.deployment import Deployment  # noqa: F401
from scene_pipelines.schemas.provenance.row_meta import RowMetaBase


@schema
class DlcProjectRowMeta(RowMetaBase):
    """Provenance for one ``DlcProject`` row."""

    tracked_table = DlcProject
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class ProjectConfigRowMeta(RowMetaBase):
    """Provenance for one ``ProjectConfig`` row."""

    tracked_table = ProjectConfig
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class PoseRowMeta(RowMetaBase):
    """Provenance for one ``Pose`` row."""

    tracked_table = Pose
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class PoseDlcProjectRowMeta(RowMetaBase):
    """Provenance for one ``PoseDlcProject`` row."""

    tracked_table = PoseDlcProject
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class PoseVideoRowMeta(RowMetaBase):
    """Provenance for one ``PoseVideo`` row."""

    tracked_table = PoseVideo
    definition = RowMetaBase.build_definition(tracked_table)
