"""Live-DB tests for register_video_recording."""

import os
import uuid
from datetime import date, datetime

import numpy as np
import pytest

pytest.importorskip("cv2")

from test_video import write_video  # noqa: E402

_TRUTHY = frozenset({"1", "true", "yes", "on"})

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.getenv("DJ_HOST"),
        reason="requires DataJoint DB (set DJ_HOST)",
    ),
    pytest.mark.skipif(
        (os.getenv("AUTO_ACTIVATE") or "").strip().lower() not in _TRUTHY,
        reason="tables are unbound unless AUTO_ACTIVATE is set",
    ),
]


@pytest.fixture
def lab(dj_connection, monkeypatch):
    """A registered lab; also sets the deployment that stamps the rows."""
    from scene_pipelines.ingestion.provenance import DuplicatePolicy
    from scene_pipelines.ingestion.scene.admin import ensure_lab

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    return ensure_lab(
        {"lab_id": "video_lab", "lab_name": "Video Lab"}, if_exists=DuplicatePolicy.SKIP
    )


@pytest.fixture
def session(lab):
    """A new session of ``lab``."""
    from scene_pipelines.ingestion import register_session

    return register_session(f"video-{uuid.uuid4().hex[:12]}", date(2026, 11, 24), lab=lab)


@pytest.fixture
def camera(lab):
    """The lab's ``top`` camera."""
    from scene_pipelines.ingestion.video import ensure_camera

    return ensure_camera("top", lab=lab, camera_details="top view")


def test_register_video_recording_links_video_to_session(session, camera, tmp_path):
    from scene_pipelines.ingestion.files import hash_file
    from scene_pipelines.ingestion.video import register_video_recording
    from scene_pipelines.schemas.video.recording import VideoRecording
    from scene_pipelines.schemas.video.row_meta import VideoRecordingRowMeta
    from scene_pipelines.schemas.video.video import VideoFile

    path = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=4)
    times = [0.0, 0.04, 0.08, 0.12]
    start = datetime(2026, 11, 24, 9, 30)
    recording = register_video_recording(
        path, session=session, camera=camera, frame_timestamps=times, start_time=start
    )

    assert recording == {**session, **camera, "take": 1}
    assert (
        register_video_recording(
            path, session=session, camera=camera, frame_timestamps=times, start_time=start
        )
        == recording
    )
    row = (VideoRecording & recording).fetch1()
    assert row["file_sha256"] == hash_file(path).sha256
    assert row["start_time"] == start
    assert VideoFile & row  # the video is registered with it
    stored = (VideoRecording.FrameTimestamps & recording).fetch1("frame_timestamps")
    np.testing.assert_array_equal(stored, times)
    assert (VideoRecordingRowMeta & recording).fetch1("origin_deployment_id") == "test-local"


def test_register_video_recording_verifies_a_registered_take(session, camera, tmp_path):
    from scene_pipelines.ingestion.provenance import DuplicatePolicy
    from scene_pipelines.ingestion.video import register_video_recording
    from scene_pipelines.schemas.video.recording import VideoRecording

    first = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=3)
    other = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=5)
    recording = register_video_recording(
        first, session=session, camera=camera, frame_timestamps=[0, 1, 2]
    )

    with pytest.raises(ValueError, match="different content hash"):
        register_video_recording(other, session=session, camera=camera)
    register_video_recording(
        first, session=session, camera=camera, if_exists=DuplicatePolicy.OVERWRITE
    )
    assert not (VideoRecording.FrameTimestamps & recording)  # overwritten without times
    second = register_video_recording(other, session=session, camera=camera, take=2)
    assert second["take"] == 2


def test_register_video_recording_warns_when_timestamps_miss_frames(session, camera, tmp_path):
    from scene_pipelines.ingestion.video import register_video_recording

    path = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=4)
    with pytest.warns(UserWarning, match="3 frame_timestamps for a video of 4 frames"):
        register_video_recording(path, session=session, camera=camera, frame_timestamps=[0, 1, 2])


def test_register_video_recording_refuses_an_unknown_session(camera, tmp_path):
    from scene_pipelines.ingestion.video import register_video_recording
    from scene_pipelines.schemas.files.files import File

    path = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=4)
    with pytest.raises(ValueError, match="no session"):
        register_video_recording(path, session={"session_id": uuid.uuid4()}, camera=camera)
    assert not (File & {"file_sha256": _sha256(path)})


def test_register_video_recording_keeps_the_file_when_the_recording_is_refused(
    session, camera, tmp_path
):
    from scene_pipelines.ingestion.video import register_video_recording
    from scene_pipelines.schemas.files.files import File
    from scene_pipelines.schemas.video.video import VideoFile

    first = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=3)
    other = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=5)
    register_video_recording(first, session=session, camera=camera)
    with pytest.raises(ValueError, match="different content hash"):
        register_video_recording(other, session=session, camera=camera)
    other_file = {"file_sha256": _sha256(other)}
    assert File & other_file
    assert not (VideoFile & other_file)  # rolled back with the refused recording


def test_register_video_recording_refuses_a_camera_of_another_lab(session, tmp_path):
    from scene_pipelines.ingestion.video import register_video_recording

    with pytest.raises(ValueError, match="of lab 'elsewhere'"):
        register_video_recording(
            tmp_path / "v.avi",
            session=session,
            camera={"lab_id": "elsewhere", "camera_code": "top"},
        )


def _sha256(path):
    from scene_pipelines.ingestion.files import hash_file

    return hash_file(path).sha256
