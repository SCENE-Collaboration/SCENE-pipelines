"""Import smoke tests (need DB config via dj_connection)."""

import importlib
import os

import pytest

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.getenv("DJ_HOST"),
        reason="requires DataJoint DB (set DJ_HOST)",
    ),
]


def test_import_lab_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.scene.lab")
    assert module is not None


def test_import_subject_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.scene.subject")
    assert module is not None


def test_import_project_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.scene.project")
    assert module is not None


def test_import_session_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.scene.session")
    assert module is not None


def test_import_deployment_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.provenance.deployment")
    assert module is not None


def test_import_row_meta_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.provenance.row_meta")
    assert module is not None


def test_import_files_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.files.files")
    assert module is not None


def test_import_video_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.video.video")
    assert module is not None


def test_import_video_recording_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.video.recording")
    assert module is not None


def test_import_video_processing_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.video.processing")
    assert module is not None


def test_import_dlc_project_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.dlc.project")
    assert module is not None


def test_import_dlc_pose_module(dj_connection):
    module = importlib.import_module("scene_pipelines.schemas.dlc.pose")
    assert module is not None
