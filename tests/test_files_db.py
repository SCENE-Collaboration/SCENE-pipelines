"""Live-DB tests for the file catalogue helpers."""

import os

import pytest

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
def store(dj_connection, monkeypatch, tmp_path):
    """Two registered stores: a disk store set as ``SCENE_STORE``, and an S3 one."""
    import datajoint as dj
    from scene_pipelines.ingestion.files.admin import ensure_store
    from scene_pipelines.ingestion.provenance import DuplicatePolicy

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_STORE", "test-disk")
    stores = {
        "test-disk": {"protocol": "file", "location": str(tmp_path / "store")},
        "test-s3": {
            "protocol": "s3",
            "endpoint": "localhost:9000",
            "bucket": "test",
            "access_key": "x",
            "secret_key": "x",
            "location": "",
        },
    }
    monkeypatch.setitem(dj.config, "stores", {**dict(dj.config.stores), **stores})
    for name, kind in (("test-disk", "file"), ("test-s3", "s3")):
        ensure_store({"store_name": name, "store_kind": kind}, if_exists=DuplicatePolicy.VERIFY)
    return tmp_path / "store"


def test_register_file_copies_and_records_once(store, tmp_path):
    from scene_pipelines.ingestion.files import locations, object_key, register_file
    from scene_pipelines.schemas.files.files import File

    path = tmp_path / "a.bin"
    path.write_bytes(b"register twice")
    file = register_file(path)
    assert register_file(path) == file

    assert len(File & file) == 1
    assert locations(file) == ["test-disk"]
    assert (store / object_key(file["file_sha256"])).read_bytes() == b"register twice"


def test_register_file_refuses_s3_stores(store, tmp_path):
    from scene_pipelines.ingestion.files import register_file

    path = tmp_path / "b.bin"
    path.write_bytes(b"upload me")
    with pytest.raises(ValueError, match="transfer job"):
        register_file(path, store="test-s3")


def test_remove_location_keeps_the_last_copy(store, tmp_path):
    from scene_pipelines.ingestion.files import (
        locations,
        record_stored,
        register_file,
        remove_location,
    )

    path = tmp_path / "c.bin"
    path.write_bytes(b"two copies")
    file = register_file(path)
    record_stored(file["file_sha256"], 10, store="test-s3")
    assert locations(file) == ["test-disk", "test-s3"]

    remove_location(file)
    assert locations(file) == ["test-s3"]
    with pytest.raises(ValueError, match="last copy"):
        remove_location(file, store="test-s3")


def test_same_hash_with_another_size_is_refused(store):
    from scene_pipelines.ingestion.files import record_stored

    sha = "f" * 64
    record_stored(sha, 10)
    with pytest.raises(ValueError, match="10 bytes"):
        record_stored(sha, 11)


def test_unknown_or_missing_store_is_refused(store, monkeypatch):
    from scene_pipelines.ingestion.files import record_stored

    with pytest.raises(ValueError, match="unknown store"):
        record_stored("e" * 64, 1, store="nowhere")
    monkeypatch.delenv("SCENE_STORE")
    with pytest.raises(ValueError, match="SCENE_STORE"):
        record_stored("e" * 64, 1)
