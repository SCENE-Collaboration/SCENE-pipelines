"""A video's frame rate, size and frame count, read with OpenCV (``scene-pipelines[video]``)."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class VideoMetadata(NamedTuple):
    """What OpenCV reports about a video."""

    fps: float
    width: int
    height: int
    n_frames: int


def read_video_metadata(path: str | Path) -> VideoMetadata:
    """Read a video's frame rate, size and frame count with OpenCV.

    Raises:
        ImportError: If OpenCV is not installed.
        ValueError: If ``path`` is not a file, OpenCV cannot open it, or it reports no frame
            rate, size or frames.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    try:
        import cv2
    except ImportError as exc:
        raise ImportError(
            'reading videos needs OpenCV: pip install "scene-pipelines[video]"'
        ) from exc

    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError(f"OpenCV cannot open the video {path}")
        metadata = VideoMetadata(
            fps=float(capture.get(cv2.CAP_PROP_FPS)),
            width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            n_frames=int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        )
    finally:
        capture.release()

    missing = [name for name, value in metadata._asdict().items() if not value > 0]
    if missing:
        raise ValueError(f"OpenCV reports no {', '.join(missing)} for the video {path}")
    return metadata
