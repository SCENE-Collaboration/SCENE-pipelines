"""Read DeepLabCut output .h5 files and DLC-live frame times; build DeepLabCut's DataFrame."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

_COORDS = ("x", "y", "likelihood")
_SINGLE_ANIMAL_LEVELS = ["scorer", "bodyparts", "coords"]
_MULTI_ANIMAL_LEVELS = ["scorer", "individuals", "bodyparts", "coords"]


@dataclass(frozen=True, eq=False)
class KeypointRecord:
    """One keypoint over all frames; arrays are float32 ``(n_frames,)``."""

    bodypart: str
    individual: str | None
    x: np.ndarray
    y: np.ndarray
    likelihood: np.ndarray


@dataclass(frozen=True, eq=False)
class PoseRecord:
    """A pose file as ``Pose`` stores it.

    Attributes:
        scorer: The ``scorer`` column level, e.g. ``DLC_Resnet50_...`` or ``DLC_live``.
        n_frames: Rows in the file.
        frame_index: int64 frame numbers from the file's index; ``None`` when they are
            ``0..n_frames-1``.
        keypoints: In the file's column order; ``individual`` is ``None`` in single-animal files.
    """

    scorer: str
    n_frames: int
    frame_index: np.ndarray | None
    keypoints: tuple[KeypointRecord, ...]


def read_pose_file(path: str | Path) -> PoseRecord:
    """Read a DeepLabCut output .h5 (offline analysis or DLC-live).

    Raises:
        ImportError: If pandas or PyTables is not installed.
        ValueError: If ``path`` is not a file or not a DeepLabCut pose file.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    pd = _import_pandas()

    try:
        frame = pd.read_hdf(path)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path} is not a DeepLabCut pose file: {exc}") from exc
    if not isinstance(frame, pd.DataFrame):
        raise ValueError(f"{path} is not a DeepLabCut pose file: not a table")
    levels = list(frame.columns.names)
    if levels not in (_SINGLE_ANIMAL_LEVELS, _MULTI_ANIMAL_LEVELS):
        raise ValueError(f"{path} has column levels {levels}, not those of a DeepLabCut pose file")
    if frame.columns.has_duplicates:
        raise ValueError(f"{path} has repeated columns")
    multianimal = levels == _MULTI_ANIMAL_LEVELS

    scorers = frame.columns.unique("scorer")
    if len(scorers) != 1:
        raise ValueError(f"{path} has {len(scorers)} scorers; expected one")
    scorer = _name(scorers[0], "scorer", max_length=255)

    n_frames = len(frame)
    if n_frames == 0:
        raise ValueError(f"{path} has no frames")
    if not pd.api.types.is_integer_dtype(frame.index):
        raise ValueError(f"{path} is not indexed by frame number (labels are not poses)")
    frame_index = frame.index.to_numpy(dtype=np.int64)
    if np.array_equal(frame_index, np.arange(n_frames)):
        frame_index = None

    grouped: dict[tuple, dict[str, np.ndarray]] = {}  # keeps column order
    for column in frame.columns:
        *names, coord = column[1:]
        grouped.setdefault(tuple(names), {})[coord] = frame[column].to_numpy(dtype=np.float32)
    keypoints = []
    for names, coords in grouped.items():
        if sorted(coords) != sorted(_COORDS):
            raise ValueError(f"{path}: keypoint {names} has coords {list(coords)}, not {_COORDS}")
        individual, bodypart = names if multianimal else (None, names[0])
        keypoints.append(
            KeypointRecord(
                bodypart=_name(bodypart, "bodypart", max_length=64),
                individual=None if individual is None else _name(individual, "individual", 64),
                **{c: coords[c] for c in _COORDS},
            )
        )
    return PoseRecord(scorer, n_frames, frame_index, tuple(keypoints))


def to_dlc_dataframe(record: PoseRecord) -> pd.DataFrame:
    """``record`` as a DataFrame in DeepLabCut's layout, indexed by frame number.

    Columns are ``scorer``, ``individuals`` (multi-animal only), ``bodyparts``, ``coords``.

    Raises:
        ImportError: If pandas is not installed.
    """
    pd = _import_pandas()
    multianimal = any(k.individual is not None for k in record.keypoints)
    columns = [
        (record.scorer, *((k.individual,) if multianimal else ()), k.bodypart, coord)
        for k in record.keypoints
        for coord in _COORDS
    ]
    values = [getattr(k, coord) for k in record.keypoints for coord in _COORDS]
    index = (
        np.arange(record.n_frames, dtype=np.int64)
        if record.frame_index is None
        else record.frame_index
    )
    return pd.DataFrame(
        np.column_stack(values),
        index=index,
        columns=pd.MultiIndex.from_tuples(
            columns, names=_MULTI_ANIMAL_LEVELS if multianimal else _SINGLE_ANIMAL_LEVELS
        ),
    )


def read_frame_times(source: str | Path | Sequence[float], *, n_frames: int) -> np.ndarray:
    """Seconds of each pose, float64 ``(n_frames,)``.

    Args:
        source: A DLC-live ``*_frame_times.csv`` (columns ``row``, ``frame_time``), or the
            times themselves.
        n_frames: Rows in the pose file.

    Raises:
        ImportError: If ``source`` is a path and pandas is not installed.
        ValueError: If the times do not match ``n_frames`` or are not finite.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise ValueError(f"not a file: {path}")
        table = _import_pandas().read_csv(path)
        if "frame_time" not in table.columns:
            raise ValueError(f"{path} has no frame_time column")
        if "row" in table.columns and not np.array_equal(table["row"], np.arange(len(table))):
            raise ValueError(f"{path}: rows are not 0..{len(table) - 1}")
        source = table["frame_time"]
    times = np.asarray(source, dtype=np.float64)
    if times.shape != (n_frames,):
        raise ValueError(f"{times.size} frame times for {n_frames} poses")
    if not np.isfinite(times).all():
        raise ValueError("frame times must be finite")
    return times


def _import_pandas():
    """pandas, with PyTables for .h5; ImportError names the extra."""
    try:
        import pandas
        import tables  # noqa: F401  # pandas reads .h5 through PyTables
    except ImportError as exc:
        raise ImportError(
            'reading DeepLabCut poses needs pandas and PyTables: pip install "scene-pipelines[dlc]"'
        ) from exc
    return pandas


def _name(value: object, field: str, max_length: int) -> str:
    """A non-empty name of at most ``max_length`` characters."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty name, not {value!r}")
    if len(value) > max_length:
        raise ValueError(f"{field} {value!r} is longer than {max_length} characters")
    return value
