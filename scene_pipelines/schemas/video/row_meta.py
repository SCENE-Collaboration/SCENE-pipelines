"""Row-level write provenance for the video tables."""

from scene_pipelines.schemas.provenance.deployment import Deployment  # noqa: F401
from scene_pipelines.schemas.provenance.row_meta import RowMetaBase
from scene_pipelines.schemas.video._schema import schema
from scene_pipelines.schemas.video.video import VideoFile


@schema
class VideoFileRowMeta(RowMetaBase):
    """Provenance for one ``VideoFile`` row."""

    tracked_table = VideoFile
    definition = RowMetaBase.build_definition(tracked_table)
