"""Row-level write provenance for the DeepLabCut tables."""

from scene_pipelines.schemas.dlc._schema import schema
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
