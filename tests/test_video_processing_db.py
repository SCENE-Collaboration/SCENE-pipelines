"""Live-DB tests for ensure_video_transform and register_processed_video."""

import os
import uuid
from datetime import date

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
def recording(lab, tmp_path):
    """A new recording in a session of the lab."""
    from scene_pipelines.ingestion import register_session
    from scene_pipelines.ingestion.video import register_video_recording

    session = register_session(f"video-{uuid.uuid4().hex[:12]}", date(2026, 11, 24), lab=lab)
    path = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=6)
    return register_video_recording(path, session=session)


def test_ensure_video_transform_refuses_other_steps_under_the_same_code(lab):
    from scene_pipelines.ingestion.video import ensure_video_transform
    from scene_pipelines.schemas.video.processing import VideoTransform

    code = f"crop-{uuid.uuid4().hex[:8]}"
    steps = [{"op": "crop", "box": [0, 0, 32, 24]}]
    transform = ensure_video_transform(code, lab=lab, transform_steps=steps)

    assert transform == {**lab, "transform_code": code}
    assert ensure_video_transform(code, lab=lab, transform_steps=steps) == transform
    assert (VideoTransform & transform).fetch1("transform_steps") == steps
    with pytest.raises(ValueError, match="different content hash"):
        ensure_video_transform(code, lab=lab, transform_steps=[{"op": "resize"}])


def test_register_processed_video_links_output_to_recording(lab, recording, tmp_path):
    from scene_pipelines.ingestion.files import hash_file
    from scene_pipelines.ingestion.video import ensure_video_transform, register_processed_video
    from scene_pipelines.schemas.video.processing import ProcessedVideo

    transform = ensure_video_transform(f"half-{uuid.uuid4().hex[:8]}", lab=lab)
    path = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=6, size=(16, 12))
    processed = register_processed_video(path, recording=recording, transform=transform)

    assert processed == {**recording, **transform}
    assert register_processed_video(path, recording=recording, transform=transform) == processed
    assert (ProcessedVideo & processed).fetch1("file_sha256") == hash_file(path).sha256


def test_register_processed_video_refuses_a_transform_of_another_lab(recording, tmp_path):
    from scene_pipelines.ingestion.files import hash_file
    from scene_pipelines.ingestion.provenance import DuplicatePolicy
    from scene_pipelines.ingestion.scene.admin import ensure_lab
    from scene_pipelines.ingestion.video import ensure_video_transform, register_processed_video
    from scene_pipelines.schemas.files.files import File

    other = ensure_lab(
        {"lab_id": "video_lab_other", "lab_name": "Other Video Lab"},
        if_exists=DuplicatePolicy.SKIP,
    )
    transform = ensure_video_transform("crop", lab=other)
    path = write_video(tmp_path / f"{uuid.uuid4().hex}.avi", n_frames=6, size=(16, 12))
    with pytest.raises(ValueError, match="of lab 'video_lab_other'"):
        register_processed_video(path, recording=recording, transform=transform)
    assert not (File & {"file_sha256": hash_file(path).sha256})  # refused before the upload
