"""Row-level write provenance for the video tables."""

from scene_pipelines.schemas.provenance.deployment import Deployment  # noqa: F401
from scene_pipelines.schemas.provenance.row_meta import RowMetaBase
from scene_pipelines.schemas.video._schema import schema
from scene_pipelines.schemas.video.processing import ProcessedVideo, VideoTransform
from scene_pipelines.schemas.video.recording import VideoRecording
from scene_pipelines.schemas.video.video import VideoFile


@schema
class VideoFileRowMeta(RowMetaBase):
    """Provenance for one ``VideoFile`` row."""

    tracked_table = VideoFile
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class VideoRecordingRowMeta(RowMetaBase):
    """Provenance for one ``VideoRecording`` row."""

    tracked_table = VideoRecording
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class VideoTransformRowMeta(RowMetaBase):
    """Provenance for one ``VideoTransform`` row."""

    tracked_table = VideoTransform
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class ProcessedVideoRowMeta(RowMetaBase):
    """Provenance for one ``ProcessedVideo`` row."""

    tracked_table = ProcessedVideo
    definition = RowMetaBase.build_definition(tracked_table)
