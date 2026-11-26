"""Register DeepLabCut output .h5 files (Pose) and their links to a project and a video."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.db import atomic
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.dlc._transient.poses import (
    PoseRecord,
    read_frame_times,
    read_pose_file,
)
from scene_pipelines.ingestion.dlc._version import DLC_WRITER_VERSION
from scene_pipelines.ingestion.files import register_file
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.schemas.dlc.pose import Pose
from scene_pipelines.schemas.dlc.project import DlcProject
from scene_pipelines.schemas.dlc.row_meta import (
    PoseDlcProjectRowMeta,
    PoseRowMeta,
    PoseVideoRowMeta,
)
from scene_pipelines.schemas.files.files import File
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.video.video import VideoFile

_POSE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "scene-pipelines/dlc/Pose")
"""Namespace of ``pose_id`` derived from a file; never change it."""


def register_pose(
    path: str | Path,
    *,
    dlc_project: DjKey[DlcProject] | None = None,
    video: DjKey[VideoFile] | None = None,
    frame_times: str | Path | Sequence[float] | None = None,
    store: bool = False,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Pose]:
    """Register a DeepLabCut output .h5: its ``File``, keypoints and optional links.

    ``pose_id`` follows from the file's SHA-256, so the same file gets the same id on every
    site. The pose, its keypoints and its links are written in one transaction.

    Args:
        path: A local DeepLabCut output .h5 (offline analysis or DLC-live).
        dlc_project: Optional existing ``DlcProject`` key, written to ``PoseDlcProject``.
        video: Optional existing ``VideoFile`` key, written to ``PoseVideo``.
        frame_times: Optional seconds of each pose: a DLC-live ``*_frame_times.csv``, or the
            times themselves.
        store: Also copy the .h5 into this deployment's store (``FileContent``).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when the pose or one of its links is already registered; see
            ``DuplicatePolicy``.

    Returns:
        ``Pose`` primary key ``{pose_id: ...}``.

    Raises:
        ImportError: If pandas or PyTables is not installed (``scene-pipelines[dlc]``).
        ValueError: If ``path`` is not a DeepLabCut pose file, a keypoint repeats,
            ``frame_times`` does not match it, the store is unusable, ``deployment`` is omitted
            and ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects an existing row.
    """
    record = read_pose_file(path)
    parts = _keypoint_parts(record)
    times = None if frame_times is None else read_frame_times(frame_times, n_frames=record.n_frames)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    file = register_file(path, store=store)
    stamp = {
        "deployment": deployment_row,
        "if_exists": if_exists,
        "writer_version": DLC_WRITER_VERSION,
    }
    fields = {
        **file,
        "scorer": record.scorer,
        "n_frames": record.n_frames,
        "frame_index": record.frame_index,
        "frame_time": times,
    }

    with atomic(Pose.connection):
        row = {"pose_id": pose_id_of_file(file), **fields}
        payload = {**file, **_payload(record, times)}
        pose = insert_tracked_row(PoseRowMeta, row, payload=payload, parts=parts, **stamp)
        if dlc_project is not None:
            project = {k: dlc_project[k] for k in ("lab_id", "dlc_project_id")}
            insert_tracked_row(PoseDlcProjectRowMeta, {**pose, **project}, payload=project, **stamp)
        if video is not None:
            link = {"video_sha256": video["file_sha256"]}
            insert_tracked_row(PoseVideoRowMeta, {**pose, **link}, payload=link, **stamp)
    return pose


def pose_id_of_file(file: DjKey[File]) -> uuid.UUID:
    """``pose_id`` of the pose read from ``file``: a UUID5 of its SHA-256."""
    return uuid.uuid5(_POSE_NAMESPACE, file["file_sha256"])


def _keypoint_parts(record: PoseRecord) -> dict:
    """Part rows of ``Pose``, in the file's column order; refuses a repeated keypoint.

    The unique index cannot: a single-animal keypoint has no individual, and nulls are distinct.
    """
    names = [(k.individual, k.bodypart) for k in record.keypoints]
    repeated = sorted({n for n in names if names.count(n) > 1}, key=str)
    if repeated:
        raise ValueError(f"repeated keypoints (individual, bodypart): {repeated}")
    return {
        Pose.Keypoint: [
            {
                "keypoint_index": i,
                "bodypart": k.bodypart,
                "individual": k.individual,
                "x": k.x,
                "y": k.y,
                "likelihood": k.likelihood,
            }
            for i, k in enumerate(record.keypoints)
        ]
    }


def _payload(record: PoseRecord, times: np.ndarray | None) -> dict:
    """Hashed fields of a pose; x, y and likelihood follow from the file, which is the key."""
    return {
        "scorer": record.scorer,
        "n_frames": record.n_frames,
        "frame_index": _array_sha256(record.frame_index),
        "frame_time": _array_sha256(times),
        "keypoints": [[k.bodypart, k.individual] for k in record.keypoints],
    }


def _array_sha256(values: np.ndarray | None) -> str | None:
    """SHA-256 of an array's bytes; ``None`` stays ``None``."""
    if values is None:
        return None
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()
