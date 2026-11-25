"""Read stored poses back as arrays or as a DeepLabCut-style DataFrame."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from scene_pipelines.core.types import DjKey
from scene_pipelines.ingestion.dlc._transient.poses import (
    KeypointRecord,
    PoseRecord,
    to_dlc_dataframe,
)
from scene_pipelines.schemas.dlc.pose import Pose

if TYPE_CHECKING:
    import pandas as pd


class KeypointTrace(NamedTuple):
    """One keypoint over all frames; float32 ``(n_frames,)`` each."""

    x: np.ndarray
    y: np.ndarray
    likelihood: np.ndarray


def keypoint(pose: DjKey[Pose], bodypart: str, individual: str | None = None) -> KeypointTrace:
    """``x``, ``y`` and ``likelihood`` of one keypoint, fetching nothing else.

    Raises:
        ValueError: If no keypoint matches, or several do and ``individual`` is omitted.
    """
    rows = Pose.Keypoint & pose & {"bodypart": bodypart}
    if individual is not None:
        rows &= {"individual": individual}
    if len(rows) != 1:
        who = bodypart if individual is None else f"{individual}/{bodypart}"
        hint = "; name the individual" if len(rows) > 1 else ""
        raise ValueError(f"{len(rows)} keypoints {who!r} in this pose{hint}")
    return KeypointTrace(*rows.fetch1("x", "y", "likelihood"))


def pose_array(pose: DjKey[Pose]) -> np.ndarray:
    """All keypoints as float32 ``(n_frames, n_keypoints, 3)`` (x, y, likelihood)."""
    rows = _keypoints(pose)
    return np.stack([np.stack([r["x"], r["y"], r["likelihood"]], axis=-1) for r in rows], axis=1)


def pose_dataframe(pose: DjKey[Pose]) -> pd.DataFrame:
    """The pose as a DataFrame in DeepLabCut's layout, indexed by frame number.

    Columns are ``scorer``, ``individuals`` (multi-animal only), ``bodyparts``, ``coords``.

    Raises:
        ImportError: If pandas or PyTables is not installed.
    """
    scorer, n_frames, frame_index = (Pose & pose).fetch1("scorer", "n_frames", "frame_index")
    keypoints = tuple(
        KeypointRecord(**{f: r[f] for f in ("bodypart", "individual", "x", "y", "likelihood")})
        for r in _keypoints(pose)
    )
    return to_dlc_dataframe(PoseRecord(scorer, n_frames, frame_index, keypoints))


def _keypoints(pose: DjKey[Pose]) -> list[dict]:
    """Keypoint rows of ``pose`` in ``keypoint_index`` order."""
    rows = (Pose.Keypoint & pose).to_dicts(order_by="keypoint_index")
    if not rows:
        raise ValueError(f"no pose {pose}")
    return rows
