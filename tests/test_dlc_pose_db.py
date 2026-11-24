"""Live-DB tests for register_pose and the pose read helpers."""

import os
import uuid

import numpy as np
import pytest

pytest.importorskip("pandas")
pytest.importorskip("tables")

from test_dlc_pose import pose_frame, write_pose  # noqa: E402

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
    return ensure_lab({"lab_id": "dlc_lab", "lab_name": "DLC Lab"}, if_exists=DuplicatePolicy.SKIP)


def new_pose_file(path, **kwargs):
    """A pose file no earlier test run has registered (its scorer is unique)."""
    return write_pose(path, pose_frame(scorer=f"test_{uuid.uuid4().hex}", **kwargs))


def test_register_pose_stores_keypoints_once(lab, tmp_path):
    from scene_pipelines.ingestion.dlc import keypoint, pose_array, pose_dataframe, register_pose
    from scene_pipelines.ingestion.dlc._transient.poses import read_pose_file
    from scene_pipelines.ingestion.files import hash_file
    from scene_pipelines.schemas.dlc.pose import Pose
    from scene_pipelines.schemas.dlc.row_meta import PoseRowMeta

    path = new_pose_file(tmp_path / "pose.h5")
    pose = register_pose(path)

    assert set(pose) == {"pose_id"}
    assert register_pose(path) == pose  # the file finds its pose again
    assert (Pose & pose).fetch1("file_sha256") == hash_file(path).sha256
    assert (Pose & pose).fetch1("n_frames", "frame_index", "frame_time") == (4, None, None)
    assert (PoseRowMeta & pose).fetch1("origin_deployment_id") == "test-local"

    record = read_pose_file(path)
    trace = keypoint(pose, "tail_base")
    assert trace.x.dtype == np.float32
    np.testing.assert_array_equal(trace.y, record.keypoints[1].y)
    assert pose_array(pose).shape == (4, 2, 3)
    np.testing.assert_array_equal(pose_array(pose)[:, 1, 2], record.keypoints[1].likelihood)

    import pandas as pd

    expected = pd.read_hdf(path).astype(np.float32)
    pd.testing.assert_frame_equal(pose_dataframe(pose), expected, check_index_type=False)


def test_register_multi_animal_pose_reads_back(lab, tmp_path):
    from scene_pipelines.ingestion.dlc import keypoint, pose_dataframe, register_pose

    path = new_pose_file(tmp_path / "pose.h5", individuals=["mouse1", "mouse2"])
    pose = register_pose(path)

    with pytest.raises(ValueError, match="name the individual"):
        keypoint(pose, "nose")
    assert keypoint(pose, "nose", "mouse2").x[0] == pytest.approx(0.2)
    assert pose_dataframe(pose).columns.names == ["scorer", "individuals", "bodyparts", "coords"]


def test_register_pose_links_project_video_and_frame_times(lab, tmp_path):
    pytest.importorskip("cv2")
    from scene_pipelines.ingestion.dlc import register_dlc_project, register_pose
    from scene_pipelines.ingestion.video import register_video
    from scene_pipelines.schemas.dlc.pose import Pose, PoseDlcProject, PoseVideo

    from test_video import write_video

    project = register_dlc_project("pose-links", lab=lab)
    other = register_dlc_project("pose-links-other", lab=lab)
    video = register_video(write_video(tmp_path / "video.avi"))
    path = new_pose_file(tmp_path / "pose.h5")
    times = [0.0, 0.04, 0.08, 0.12]

    pose = register_pose(path, dlc_project=project, video=video, frame_times=times)

    assert (PoseDlcProject & pose).fetch1("dlc_project_id") == project["dlc_project_id"]
    assert (PoseVideo & pose).fetch1("video_sha256") == video["file_sha256"]
    np.testing.assert_array_equal((Pose & pose).fetch1("frame_time"), times)
    assert register_pose(path, dlc_project=project, video=video, frame_times=times) == pose
    with pytest.raises(ValueError, match="different content hash"):
        register_pose(path, dlc_project=other, video=video, frame_times=times)
    with pytest.raises(ValueError, match="different content hash"):
        register_pose(path, dlc_project=project, video=video)  # frame times differ
    assert (PoseDlcProject & pose).fetch1("dlc_project_id") == project["dlc_project_id"]


def test_link_added_to_a_pose_registered_without_one(lab, tmp_path):
    from scene_pipelines.ingestion.dlc import register_dlc_project, register_pose
    from scene_pipelines.schemas.dlc.pose import PoseDlcProject

    path = new_pose_file(tmp_path / "pose.h5")
    pose = register_pose(path)
    assert not (PoseDlcProject & pose)
    project = register_dlc_project("pose-later-link", lab=lab)
    assert register_pose(path, dlc_project=project) == pose
    assert PoseDlcProject & pose
