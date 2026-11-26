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


def test_ensure_video_transform_refuses_an_invalid_code():
    with pytest.raises(ValueError, match="transform_code"):
        processing_module.ensure_video_transform("crop arena", lab={"lab_id": "lab"})


@pytest.mark.parametrize("table", [VideoTransform, ProcessedVideo])
def test_processing_tables_are_acquired_origin_data(table):
    assert sync_authority_of(table) is SyncAuthority.ORIGIN
    assert write_role_of(table) is WriteRole.ACQUISITION
