"""Register a lab's video processing recipes (VideoTransform) and their output (ProcessedVideo)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.db import atomic
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.files import register_file
from scene_pipelines.ingestion.normalization.code import normalize_code
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.ingestion.video._transient.metadata import read_video_metadata
from scene_pipelines.ingestion.video._version import VIDEO_WRITER_VERSION
from scene_pipelines.ingestion.video.video import insert_video_file
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.scene.lab import Lab
from scene_pipelines.schemas.scene.session import Session
from scene_pipelines.schemas.video.processing import ProcessedVideo, VideoTransform
from scene_pipelines.schemas.video.recording import VideoRecording
from scene_pipelines.schemas.video.row_meta import ProcessedVideoRowMeta, VideoTransformRowMeta


def ensure_video_transform(
    transform_code: str,
    *,
    lab: DjKey[Lab],
    transform_name: str = "",
    transform_steps: list[Any] | dict[str, Any] | None = None,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[VideoTransform]:
    """Register a lab's video processing recipe by its code.

    Args:
        transform_code: Code unique within ``lab``; see ``normalize_code``.
        lab: Existing lab primary key.
        transform_name: Optional readable name.
        transform_steps: Optional JSON-serialisable description of the steps.
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when the code is already registered in ``lab``; with the default,
            a code registered with other steps is refused.

    Returns:
        ``VideoTransform`` primary key.

    Raises:
        ValueError: If ``transform_code`` is not a valid code, ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects the existing row.
    """
    code = normalize_code(transform_code, field="transform_code", max_length=64)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    fields = {"transform_name": transform_name, "transform_steps": transform_steps}
    return insert_tracked_row(
        VideoTransformRowMeta,
        {"lab_id": lab["lab_id"], "transform_code": code, **fields},
        payload=fields,
        deployment=deployment_row,
        if_exists=if_exists,
        writer_version=VIDEO_WRITER_VERSION,
    )


def register_processed_video(
    path: str | Path,
    *,
    recording: DjKey[VideoRecording],
    transform: DjKey[VideoTransform],
    store: bool = False,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[ProcessedVideo]:
    """Register the video a transform made from a recording: its ``VideoFile`` and the link.

    The file is registered first (its upload cannot be rolled back); ``VideoFile`` and
    ``ProcessedVideo`` are then written in one transaction.

    Args:
        path: The processed video, a local file.
        recording: Existing ``VideoRecording`` key.
        transform: Existing ``VideoTransform`` key of the recording's lab.
        store: Also copy the bytes into this deployment's store (``FileContent``).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when this recording and transform already have a processed video;
            see ``DuplicatePolicy``.

    Returns:
        ``ProcessedVideo`` primary key.

    Raises:
        ImportError: If OpenCV is not installed (``scene-pipelines[video]``).
        ValueError: If the transform belongs to another lab than the recording, the video is
            unreadable, or ``if_exists`` rejects the existing row.
    """
    session_lab = (Session & {"session_id": recording["session_id"]}).fetch1("lab_id")
    if transform["lab_id"] != session_lab:
        raise ValueError(
            f"transform {transform['transform_code']!r} is of lab {transform['lab_id']!r}, "
            f"the recording of lab {session_lab!r}"
        )
    metadata = read_video_metadata(path)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    file = register_file(path, store=store)
    key = {
        "session_id": recording["session_id"],
        "take": recording["take"],
        "lab_id": transform["lab_id"],
        "transform_code": transform["transform_code"],
    }
    with atomic(ProcessedVideo.connection):
        insert_video_file(file, metadata, deployment=deployment_row)
        return insert_tracked_row(
            ProcessedVideoRowMeta,
            {**key, **file},
            payload=file,
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=VIDEO_WRITER_VERSION,
        )
