"""Unit tests for the pose reader and register_pose (no database)."""

import sys

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("tables")

from scene_pipelines.core.access_markers import (  # noqa: E402
    SyncAuthority,
    WriteRole,
    sync_authority_of,
    write_role_of,
)
from scene_pipelines.ingestion.dlc import pose as pose_module  # noqa: E402
from scene_pipelines.ingestion.dlc._transient.poses import (  # noqa: E402
    read_frame_times,
    read_pose_file,
    to_dlc_dataframe,
)
from scene_pipelines.schemas.dlc.pose import Pose, PoseDlcProject, PoseVideo  # noqa: E402

SCORER = "DLC_Resnet50_reachJun26shuffle1_snapshot_best-100"


def pose_frame(n_frames=4, *, scorer=SCORER, individuals=None, bodyparts=("nose", "tail_base")):
    """A DeepLabCut pose table; values are ``frame + keypoint / 10`` (float64, like DLC-live)."""
    names = [(i, b) for i in individuals for b in bodyparts] if individuals else list(bodyparts)
    columns = [
        (scorer, *(n if individuals else (n,)), coord)
        for n in names
        for coord in ("x", "y", "likelihood")
    ]
    levels = ["scorer", "individuals", "bodyparts", "coords"] if individuals else None
    levels = levels or ["scorer", "bodyparts", "coords"]
    values = np.arange(n_frames)[:, None] + np.repeat(np.arange(len(names)), 3)[None, :] / 10
    return pd.DataFrame(values, columns=pd.MultiIndex.from_tuples(columns, names=levels))


def write_pose(path, frame=None):
    """Write ``frame`` (default ``pose_frame()``) as a DeepLabCut .h5; returns its path."""
    (pose_frame() if frame is None else frame).to_hdf(path, key="df_with_missing", mode="w")
    return path


def test_read_single_animal_pose(tmp_path):
    record = read_pose_file(write_pose(tmp_path / "pose.h5"))

    assert (record.scorer, record.n_frames, record.frame_index) == (SCORER, 4, None)
    assert [(k.bodypart, k.individual) for k in record.keypoints] == [
        ("nose", None),
        ("tail_base", None),
    ]
    tail = record.keypoints[1]
    assert tail.x.dtype == np.float32
    np.testing.assert_allclose(tail.y, np.arange(4) + 0.1, rtol=1e-6)


def test_read_multi_animal_pose_keeps_column_order(tmp_path):
    frame = pose_frame(individuals=["mouse2", "mouse1"])
    single = pose_frame(scorer=SCORER, individuals=["single"], bodyparts=["port"])
    record = read_pose_file(write_pose(tmp_path / "pose.h5", pd.concat([frame, single], axis=1)))

    assert [(k.individual, k.bodypart) for k in record.keypoints] == [
        ("mouse2", "nose"),
        ("mouse2", "tail_base"),
        ("mouse1", "nose"),
        ("mouse1", "tail_base"),
        ("single", "port"),
    ]


def test_read_pose_keeps_frame_numbers_that_are_not_0_to_n(tmp_path):
    frame = pose_frame().set_axis([10, 11, 12, 14])
    record = read_pose_file(write_pose(tmp_path / "pose.h5", frame))
    np.testing.assert_array_equal(record.frame_index, [10, 11, 12, 14])
    assert record.frame_index.dtype == np.int64


@pytest.mark.parametrize(
    "frame",
    [
        pose_frame(),
        pose_frame(individuals=["mouse1", "mouse2"]),
        pose_frame().set_axis([10, 11, 12, 14]),
    ],
)
def test_dlc_dataframe_gives_back_the_file(tmp_path, frame):
    path = write_pose(tmp_path / "pose.h5", frame)
    expected = pd.read_hdf(path).astype(np.float32)
    pd.testing.assert_frame_equal(to_dlc_dataframe(read_pose_file(path)), expected)


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (pose_frame().iloc[:, :-1], "coords"),
        (pose_frame().set_axis(["a.png", "b.png", "c.png", "d.png"]), "frame number"),
        (pose_frame(0), "no frames"),
        (
            pd.concat([pose_frame(), pose_frame(scorer="other", bodyparts=["ear"])], axis=1),
            "scorers",
        ),
        (pose_frame().droplevel("scorer", axis=1), "column levels"),
        (pose_frame(bodyparts=["x" * 65]), "longer than 64"),
    ],
)
def test_read_pose_refuses_what_is_no_pose_file(tmp_path, frame, message):
    with pytest.raises(ValueError, match=message):
        read_pose_file(write_pose(tmp_path / "pose.h5", frame))


def test_read_pose_refuses_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        read_pose_file(tmp_path / "pose.h5")


def test_read_pose_names_the_extra_without_pytables(tmp_path, monkeypatch):
    path = write_pose(tmp_path / "pose.h5")
    monkeypatch.setitem(sys.modules, "tables", None)  # makes the import raise ImportError
    with pytest.raises(ImportError, match=r"scene-pipelines\[dlc\]"):
        read_pose_file(path)


def test_read_dlc_live_frame_times(tmp_path):
    path = tmp_path / "live_frame_times.csv"
    path.write_text("row,frame_time\n0,1793693129.20\n1,1793693129.67\n", encoding="utf-8")
    times = read_frame_times(path, n_frames=2)
    assert times.dtype == np.float64
    np.testing.assert_array_equal(times, [1793693129.20, 1793693129.67])
    np.testing.assert_array_equal(read_frame_times([0.0, 0.5], n_frames=2), [0.0, 0.5])


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("row,frame_time\n0,1.0\n", "1 frame times for 2 poses"),
        ("row,frame_time\n1,1.0\n0,2.0\n", "rows are not"),
        ("row,time\n0,1.0\n1,2.0\n", "no frame_time column"),
        ("row,frame_time\n0,1.0\n1,\n", "finite"),
    ],
)
def test_read_frame_times_refuses_what_does_not_match(tmp_path, text, message):
    path = tmp_path / "frame_times.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        read_frame_times(path, n_frames=2)


def test_register_pose_writes_nothing_when_frame_times_do_not_match(tmp_path, monkeypatch):
    def must_not_register(path, *, store):
        raise AssertionError("File was written for a pose that was refused")

    monkeypatch.setattr(pose_module, "register_file", must_not_register)
    with pytest.raises(ValueError, match="frame times"):
        pose_module.register_pose(write_pose(tmp_path / "pose.h5"), frame_times=[0.0, 1.0])


def test_payload_covers_keypoints_and_frames_but_not_values(tmp_path):
    record = read_pose_file(write_pose(tmp_path / "pose.h5"))
    payload = pose_module._payload(record, None)
    assert payload["keypoints"] == [["nose", None], ["tail_base", None]]
    assert (payload["frame_index"], payload["frame_time"]) == (None, None)
    assert pose_module._payload(record, np.zeros(4))["frame_time"] is not None


def test_keypoint_parts_keep_column_order(tmp_path):
    record = read_pose_file(write_pose(tmp_path / "pose.h5"))
    parts = pose_module._keypoint_parts(record)[Pose.Keypoint]
    assert [(p["keypoint_index"], p["bodypart"]) for p in parts] == [(0, "nose"), (1, "tail_base")]


@pytest.mark.parametrize("table", [Pose, Pose.Keypoint, PoseDlcProject, PoseVideo])
def test_pose_tables_are_acquired_origin_data(table):
    assert sync_authority_of(table) is SyncAuthority.ORIGIN
    assert write_role_of(table) is WriteRole.ACQUISITION
