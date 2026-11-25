"""Register a lab's cameras (Camera) and the videos they record in a session (VideoRecording)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import numpy as np

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.db import atomic
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.normalization.code import normalize_code
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.ingestion.video._version import VIDEO_WRITER_VERSION
from scene_pipelines.ingestion.video.video import register_video
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.scene.lab import Lab
from scene_pipelines.schemas.scene.session import Session
from scene_pipelines.schemas.video.recording import Camera, VideoRecording
from scene_pipelines.schemas.video.row_meta import CameraRowMeta, VideoRecordingRowMeta


def ensure_camera(
    camera_code: str,
    *,
    lab: DjKey[Lab],
    camera_details: str = "",
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Camera]:
    """Register a lab's camera or view by its code.

    Args:
        camera_code: Code unique within ``lab``, e.g. ``top``; see ``normalize_code``.
        lab: Existing lab primary key.
        camera_details: Optional free-text description.
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when the code is already registered in ``lab``; see
            ``DuplicatePolicy``.

    Returns:
        ``Camera`` primary key.

    Raises:
        ValueError: If ``camera_code`` is not a valid code, ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects the existing row.
    """
    code = normalize_code(camera_code, field="camera_code", max_length=32)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    return insert_tracked_row(
        CameraRowMeta,
        {"lab_id": lab["lab_id"], "camera_code": code, "camera_details": camera_details},
        payload={"camera_details": camera_details},
        deployment=deployment_row,
        if_exists=if_exists,
        writer_version=VIDEO_WRITER_VERSION,
    )


def register_video_recording(
    path: str | Path,
    *,
    session: DjKey[Session],
    camera: DjKey[Camera],
    take: int = 1,
    frame_timestamps: Sequence[float] | None = None,
    start_time: datetime | None = None,
    store: bool = False,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[VideoRecording]:
    """Register a video recorded in a session: its ``VideoFile`` and the recording.

    Args:
        path: A local video file.
        session: Existing ``Session`` key.
        camera: Existing ``Camera`` key of the session's lab.
        take: 1, 2, ... per camera in the session, in start order.
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
        ValueError: If ``take`` is below 1, ``frame_timestamps`` are not finite, the camera
            belongs to another lab than the session, the video is unreadable, or
            ``if_exists`` rejects the existing row.
    """
    if take < 1:
        raise ValueError(f"take must be 1 or more, not {take}")
    times = None if frame_timestamps is None else _timestamps(frame_timestamps)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    session_lab = (Session & session).fetch1("lab_id")
    if camera["lab_id"] != session_lab:
        raise ValueError(
            f"camera {camera['camera_code']!r} is of lab {camera['lab_id']!r}, "
            f"the session of lab {session_lab!r}"
        )

    video = register_video(path, store=store, deployment=deployment_row)
    key = {"session_id": session["session_id"], **camera, "take": take}
    row = {**key, **video, "start_time": start_time}
    payload = {
        "file_sha256": video["file_sha256"],
        "start_time": start_time,
        "frame_timestamps": None if times is None else _sha256(times),
    }
    parts = {VideoRecording.FrameTimestamps: [] if times is None else [{"frame_timestamps": times}]}
    with atomic(VideoRecording.connection):
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
