"""Unit tests for VideoRecording and its helper (no database)."""

import pytest
from scene_pipelines.core.access_markers import (
    SyncAuthority,
    WriteRole,
    sync_authority_of,
    write_role_of,
)
from scene_pipelines.ingestion.video import recording as recording_module
from scene_pipelines.schemas.video.recording import Camera, VideoRecording

SESSION = {"session_id": "00000000-0000-0000-0000-000000000001"}
CAMERA = {"lab_id": "lab", "camera_code": "top"}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"take": 0}, "take must be 1 or more"),
        ({"frame_timestamps": [0.0, float("nan")]}, "finite"),
        ({"frame_timestamps": [[0.0, 1.0]]}, "finite"),
    ],
)
def test_register_video_recording_refuses_bad_arguments(tmp_path, kwargs, message):
    with pytest.raises(ValueError, match=message):
        recording_module.register_video_recording(
            tmp_path / "v.avi", session=SESSION, camera=CAMERA, **kwargs
        )


@pytest.mark.parametrize("table", [Camera, VideoRecording, VideoRecording.FrameTimestamps])
def test_recording_tables_are_acquired_origin_data(table):
    assert sync_authority_of(table) is SyncAuthority.ORIGIN
    assert write_role_of(table) is WriteRole.ACQUISITION
