"""Register the videos recorded in a session (VideoRecording)."""

from __future__ import annotations

import hashlib
import warnings
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import numpy as np

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.db import atomic
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.files import register_file
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.ingestion.video._transient.metadata import read_video_metadata
from scene_pipelines.ingestion.video._version import VIDEO_WRITER_VERSION
from scene_pipelines.ingestion.video.video import insert_video_file
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.scene.session import Session
from scene_pipelines.schemas.video.recording import VideoRecording
from scene_pipelines.schemas.video.row_meta import VideoRecordingRowMeta


def register_video_recording(
    path: str | Path,
    *,
    session: DjKey[Session],
    take: int = 1,
    frame_timestamps: Sequence[float] | None = None,
    start_time: datetime | None = None,
    store: bool = False,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[VideoRecording]:
    """Register a video recorded in a session: its ``VideoFile`` and the recording.

    The file is registered first (its upload cannot be rolled back); ``VideoFile`` and the
    recording are then written in one transaction. Warns when the number of
    ``frame_timestamps`` differs from the frame count OpenCV reports.

    Args:
        path: A local video file.
        session: Existing ``Session`` key.
        take: 1, 2, ... per session, numbered by the lab.
        frame_timestamps: Optional seconds of each frame, on the recorder's clock.
        start_time: Optional start of the recording, on the recorder's clock.
        store: Also copy the bytes into this deployment's store (``FileContent``).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when this take is already registered; see ``DuplicatePolicy``.

    Returns:
        ``VideoRecording`` primary key.

    Raises:
        ImportError: If OpenCV is not installed (``scene-pipelines[video]``).
        ValueError: If ``take`` is below 1, ``frame_timestamps`` are not finite, the session
            is not registered, the video is unreadable, or ``if_exists`` rejects the
            existing row.
    """
    if take < 1:
        raise ValueError(f"take must be 1 or more, not {take}")
    times = None if frame_timestamps is None else _timestamps(frame_timestamps)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    if not Session & {"session_id": session["session_id"]}:
        raise ValueError(f"no session {session['session_id']}")
    metadata = read_video_metadata(path)
    if times is not None and len(times) != metadata.n_frames:
        warnings.warn(
            f"{len(times)} frame_timestamps for a video of {metadata.n_frames} frames "
            "(as OpenCV counts them)",
            stacklevel=2,
        )

    file = register_file(path, store=store)
    key = {"session_id": session["session_id"], "take": take}
    row = {**key, **file, "start_time": start_time}
    payload = {
        "file_sha256": file["file_sha256"],
        "start_time": start_time,
        "frame_timestamps": None if times is None else _sha256(times),
    }
    parts = {VideoRecording.FrameTimestamps: [] if times is None else [{"frame_timestamps": times}]}
    with atomic(VideoRecording.connection):
        insert_video_file(file, metadata, deployment=deployment_row)
        return insert_tracked_row(
            VideoRecordingRowMeta,
            row,
            payload=payload,
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=VIDEO_WRITER_VERSION,
            parts=parts,
        )


def _timestamps(values: Sequence[float]) -> np.ndarray:
    """Frame times as a finite float64 vector."""
    times = np.asarray(values, dtype=np.float64)
    if times.ndim != 1 or not np.isfinite(times).all():
        raise ValueError("frame_timestamps must be a list of finite seconds")
    return times


def _sha256(values: np.ndarray) -> str:
    """SHA-256 of an array's bytes."""
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()
