"""Unit tests for provenance row-meta table definitions (no MySQL)."""

from __future__ import annotations

import pytest
from scene_pipelines.schemas.dlc.row_meta import (
    DlcProjectRowMeta,
    PoseDlcProjectRowMeta,
    PoseRowMeta,
    PoseVideoRowMeta,
    ProjectConfigRowMeta,
)
from scene_pipelines.schemas.mouse.row_meta import MouseRowMeta, StrainRowMeta
from scene_pipelines.schemas.provenance.row_meta import (
    LabRowMeta,
    ProjectRowMeta,
    RowMetaBase,
    SessionRowMeta,
    SubjectRowMeta,
)
from scene_pipelines.schemas.video.row_meta import (
    CameraRowMeta,
    ProcessedVideoRowMeta,
    VideoFileRowMeta,
    VideoRecordingRowMeta,
    VideoTransformRowMeta,
)

_STAMP_COLUMNS = (
    "-> Deployment",
    "ingestion_version: varchar(32)",
    "content_hash: char(64)",
    "hash_version: smallint unsigned",
    "updated_at: datetime",
    "-> Deployment.proj(origin_deployment_id='deployment_id')",
    "created_at: datetime",
)


def test_row_meta_tracked_tables() -> None:
    for row_meta_table in RowMetaBase.__subclasses__():
        expected_parent = f"-> {row_meta_table.tracked_table.__name__}"

        assert row_meta_table.definition.lstrip().startswith(expected_parent), (
            f"{row_meta_table.__name__} tracks "
            f"{row_meta_table.tracked_table.__name__}, but its definition is "
            f"{row_meta_table.definition!r}"
        )


def test_row_meta_subclasses_match_tracked_masters() -> None:
    # Only this package's: a process may also import a lab package's row-meta tables.
    ours = {c for c in RowMetaBase.__subclasses__() if c.__module__.startswith("scene_pipelines.")}
    assert ours == {
        LabRowMeta,
        SubjectRowMeta,
        ProjectRowMeta,
        SessionRowMeta,
        MouseRowMeta,
        StrainRowMeta,
        VideoFileRowMeta,
        CameraRowMeta,
        VideoRecordingRowMeta,
        VideoTransformRowMeta,
        ProcessedVideoRowMeta,
        DlcProjectRowMeta,
        ProjectConfigRowMeta,
        PoseRowMeta,
        PoseDlcProjectRowMeta,
        PoseVideoRowMeta,
    }
    assert LabRowMeta.tracked_table.__name__ == "Lab"
    assert SubjectRowMeta.tracked_table.__name__ == "Subject"
    assert ProjectRowMeta.tracked_table.__name__ == "Project"
    assert SessionRowMeta.tracked_table.__name__ == "Session"
    assert MouseRowMeta.tracked_table.__name__ == "Mouse"
    assert StrainRowMeta.tracked_table.__name__ == "Strain"
    assert VideoFileRowMeta.tracked_table.__name__ == "VideoFile"
    assert CameraRowMeta.tracked_table.__name__ == "Camera"
    assert VideoRecordingRowMeta.tracked_table.__name__ == "VideoRecording"
    assert VideoTransformRowMeta.tracked_table.__name__ == "VideoTransform"
    assert ProcessedVideoRowMeta.tracked_table.__name__ == "ProcessedVideo"
    assert DlcProjectRowMeta.tracked_table.__name__ == "DlcProject"
    assert ProjectConfigRowMeta.tracked_table.__name__ == "ProjectConfig"
    assert PoseRowMeta.tracked_table.__name__ == "Pose"
    assert PoseDlcProjectRowMeta.tracked_table.__name__ == "PoseDlcProject"
    assert PoseVideoRowMeta.tracked_table.__name__ == "PoseVideo"


def test_definition_is_built_from_tracked_table_and_shared_attrs() -> None:
    for column in _STAMP_COLUMNS:
        assert column in RowMetaBase.ROW_META_ATTRS
    for row_meta_table in RowMetaBase.__subclasses__():
        assert row_meta_table.definition == RowMetaBase.build_definition(
            row_meta_table.tracked_table
        )


def test_tracked_key_returns_only_primary_key_fields() -> None:
    class _Tracked:
        primary_key = ["lab_id", "session_id"]

    class _Meta:
        tracked_table = _Tracked

    tracked_key = RowMetaBase.tracked_key.__func__
    row = {
        "lab_id": "mlai",
        "session_id": "abc",
        "session_code": "morning",
    }
    assert tracked_key(_Meta, row) == {"lab_id": "mlai", "session_id": "abc"}


def test_tracked_key_requires_primary_key_fields() -> None:
    class _Tracked:
        primary_key = ["subject_id"]

    class _Meta:
        tracked_table = _Tracked

    with pytest.raises(KeyError):
        RowMetaBase.tracked_key.__func__(_Meta, {"subject_kind": "mouse"})
