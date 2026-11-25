"""Unit tests for VideoTransform, ProcessedVideo and their helpers (no database)."""

import pytest
from scene_pipelines.core.access_markers import (
    SyncAuthority,
    WriteRole,
    sync_authority_of,
    write_role_of,
)
from scene_pipelines.ingestion.video import processing as processing_module
from scene_pipelines.schemas.video.processing import ProcessedVideo, VideoTransform

RECORDING = {
    "session_id": "00000000-0000-0000-0000-000000000001",
    "lab_id": "lab",
    "camera_code": "top",
    "take": 1,
}


def test_ensure_video_transform_refuses_an_invalid_code():
    with pytest.raises(ValueError, match="transform_code"):
        processing_module.ensure_video_transform("crop arena", lab={"lab_id": "lab"})


def test_register_processed_video_refuses_a_transform_of_another_lab(tmp_path, monkeypatch):
    def must_not_register(*args, **kwargs):
        raise AssertionError("File was written for a refused processed video")

    monkeypatch.setattr(processing_module, "register_file", must_not_register)
    transform = {"lab_id": "elsewhere", "transform_code": "crop"}
    with pytest.raises(ValueError, match="of lab 'elsewhere'"):
        processing_module.register_processed_video(
            tmp_path / "v.avi", recording=RECORDING, transform=transform
        )


@pytest.mark.parametrize("table", [VideoTransform, ProcessedVideo])
def test_processing_tables_are_acquired_origin_data(table):
    assert sync_authority_of(table) is SyncAuthority.ORIGIN
    assert write_role_of(table) is WriteRole.ACQUISITION
