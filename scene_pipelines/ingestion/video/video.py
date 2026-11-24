"""Register videos in ``VideoFile``."""

from __future__ import annotations

from pathlib import Path

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.files import register_file
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.ingestion.video._transient.metadata import read_video_metadata
from scene_pipelines.ingestion.video._version import VIDEO_WRITER_VERSION
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.video.row_meta import VideoFileRowMeta
from scene_pipelines.schemas.video.video import VideoFile


def register_video(
    path: str | Path,
    *,
    store: bool = False,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.SKIP,
) -> DjKey[VideoFile]:
    """Register a local video: its ``File`` and the metadata read from it.

    Args:
        path: A local video file.
        store: Also copy the bytes into this deployment's store (``FileContent``).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when the video is already registered; see ``DuplicatePolicy``.

    Returns:
        ``VideoFile`` key.

    Raises:
        ImportError: If OpenCV is not installed (``scene-pipelines[video]``).
        ValueError: If ``path`` is not a video OpenCV can read, the store is unusable,
            ``deployment`` is omitted and ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists``
            rejects the existing row.
    """
    metadata = read_video_metadata(path)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    file = register_file(path, store=store)
    return insert_tracked_row(
        VideoFileRowMeta,
        {**file, **metadata._asdict()},
        payload=metadata._asdict(),
        deployment=deployment_row,
        if_exists=if_exists,
        writer_version=VIDEO_WRITER_VERSION,
    )
