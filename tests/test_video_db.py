"""Live-DB tests for the video helpers."""

import os

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


@pytest.fixture(autouse=True)
def deployment(monkeypatch):
    """The deployment that stamps the rows these tests write."""
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")


@pytest.fixture
def file_store(dj_connection, monkeypatch, tmp_path):
    """A prepared ``scene-files`` store on disk, as in ``test_files_db``."""
    import datajoint as dj
    from scene_pipelines.ingestion.files import FILE_STORE
    from scene_pipelines.ingestion.files.admin import init_file_store

    root = tmp_path / "store"
    root.mkdir()
    store = {"protocol": "file", "location": str(root), "filepath_prefix": "sha256"}
    monkeypatch.setitem(dj.config, "stores", {**dict(dj.config.stores), FILE_STORE: store})
    init_file_store(new_copy=True)
    return root


def test_register_video_records_file_and_metadata_once(dj_connection, tmp_path):
    from scene_pipelines.ingestion.files import hash_file
    from scene_pipelines.ingestion.video import VIDEO_WRITER_VERSION, register_video
    from scene_pipelines.schemas.files.files import File, FileContent
    from scene_pipelines.schemas.video.row_meta import VideoFileRowMeta
    from scene_pipelines.schemas.video.video import VideoFile

    path = write_video(tmp_path / "once.avi", n_frames=12, size=(40, 30), fps=30.0)
    video = register_video(path)

    assert video == {"file_sha256": hash_file(path).sha256}
    assert register_video(path) == video
    assert len(VideoFile & video) == 1
    assert (VideoFile & video).fetch1("fps", "width", "height", "n_frames") == (30.0, 40, 30, 12)
    assert File & video
    assert not (FileContent & video)  # store=False by default: bytes stay where they are
    stamp = (VideoFileRowMeta & video).fetch1()
    assert stamp["origin_deployment_id"] == "test-local"
    assert stamp["ingestion_version"] == VIDEO_WRITER_VERSION


def test_register_video_can_store_the_bytes(file_store, tmp_path):
    from scene_pipelines.ingestion.video import register_video
    from scene_pipelines.schemas.files.files import FileContent

    path = write_video(tmp_path / "stored.avi", n_frames=5)
    video = register_video(path, store=True)

    assert FileContent & video


def test_register_video_keeps_an_existing_row(dj_connection, tmp_path, monkeypatch):
    from scene_pipelines.ingestion.provenance import DuplicatePolicy
    from scene_pipelines.ingestion.video import register_video
    from scene_pipelines.ingestion.video import video as video_module
    from scene_pipelines.ingestion.video._transient.metadata import VideoMetadata
    from scene_pipelines.schemas.video.video import VideoFile

    path = write_video(tmp_path / "kept.avi", n_frames=7)
    video = register_video(path)
    monkeypatch.setattr(
        video_module, "read_video_metadata", lambda path: VideoMetadata(1.0, 2, 3, 4)
    )

    assert register_video(path) == video  # SKIP is the default
    assert (VideoFile & video).fetch1("n_frames") == 7
    with pytest.raises(ValueError, match="different content hash"):
        register_video(path, if_exists=DuplicatePolicy.VERIFY)
