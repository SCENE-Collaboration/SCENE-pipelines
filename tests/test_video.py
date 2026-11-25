"""Unit tests for the video schema and helpers (no database)."""

import sys

import numpy as np
import pytest
from scene_pipelines.core.access_markers import (
    SyncAuthority,
    WriteRole,
    sync_authority_of,
    write_role_of,
)
from scene_pipelines.ingestion.video import video as video_module
from scene_pipelines.ingestion.video._transient.metadata import VideoMetadata, read_video_metadata
from scene_pipelines.schemas.video.row_meta import VideoFileRowMeta
from scene_pipelines.schemas.video.video import VideoFile


def write_video(path, *, n_frames=10, size=(32, 24), fps=25.0):
    """Write a small MJPG video with OpenCV; returns its path."""
    cv2 = pytest.importorskip("cv2")
    width, height = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    assert writer.isOpened()
    for i in range(n_frames):
        writer.write(np.full((height, width, 3), i * 20, dtype=np.uint8))
    writer.release()
    return path


def test_read_video_metadata(tmp_path):
    path = write_video(tmp_path / "v.avi", n_frames=10, size=(32, 24), fps=25.0)
    assert read_video_metadata(path) == VideoMetadata(fps=25.0, width=32, height=24, n_frames=10)


def test_read_video_metadata_refuses_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        read_video_metadata(tmp_path / "missing.avi")


def test_read_video_metadata_refuses_a_file_that_is_no_video(tmp_path):
    pytest.importorskip("cv2")
    path = tmp_path / "notes.avi"
    path.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="OpenCV"):
        read_video_metadata(path)


def test_read_video_metadata_names_the_extra_without_opencv(tmp_path, monkeypatch):
    path = tmp_path / "v.avi"
    path.write_bytes(b"")
    monkeypatch.setitem(sys.modules, "cv2", None)  # makes `import cv2` raise ImportError
    with pytest.raises(ImportError, match=r"scene-pipelines\[video\]"):
        read_video_metadata(path)


def test_register_video_writes_nothing_for_an_unreadable_video(tmp_path, monkeypatch):
    def refuse(path):
        raise ValueError("unreadable")

    def must_not_register(path, *, store):
        raise AssertionError("File was written for an unreadable video")

    monkeypatch.setattr(video_module, "read_video_metadata", refuse)
    monkeypatch.setattr(video_module, "register_file", must_not_register)
    with pytest.raises(ValueError, match="unreadable"):
        video_module.register_video(tmp_path / "v.avi")


def test_video_file_is_acquired_shared_data_and_stamped():
    assert sync_authority_of(VideoFile) is SyncAuthority.SHARED
    assert write_role_of(VideoFile) is WriteRole.ACQUISITION
    assert VideoFileRowMeta.tracked_table is VideoFile


def test_video_file_is_keyed_by_its_file():
    definition = VideoFile.definition
    assert definition.split("---")[0].split() == ["->", "File"]
