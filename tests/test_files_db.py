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
def stores(dj_connection, monkeypatch, tmp_path):
    """Registered stores: two disk stores, one unmounted, one with the wrong kind."""
    import datajoint as dj
    from scene_pipelines.ingestion.files.admin import ensure_store
    from scene_pipelines.ingestion.provenance import DuplicatePolicy

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    roots = {name: tmp_path / name for name in ("test-disk-a", "test-disk-b")}
    for root in roots.values():
        root.mkdir()
    configured = {
        **{name: {"protocol": "file", "location": str(root)} for name, root in roots.items()},
        "test-unmounted": {"protocol": "file", "location": str(tmp_path / "not-mounted")},
        "test-wrong-kind": {"protocol": "file", "location": str(tmp_path)},
    }
    monkeypatch.setitem(dj.config, "stores", {**dict(dj.config.stores), **configured})
    for name, kind in (
        ("test-disk-a", "file"),
        ("test-disk-b", "file"),
        ("test-unmounted", "file"),
        ("test-wrong-kind", "s3"),
    ):
        ensure_store({"store_name": name, "store_kind": kind}, if_exists=DuplicatePolicy.VERIFY)
    return roots


def test_register_file_copies_and_records_once(stores, tmp_path):
    from scene_pipelines.ingestion.files import locations, object_key, register_file
    from scene_pipelines.schemas.files.files import File

    path = tmp_path / "a.bin"
    path.write_bytes(b"register twice")
    file = register_file(path, store="test-disk-a")
    assert register_file(path, store="test-disk-a") == file

    assert len(File & file) == 1
    assert locations(file) == ["test-disk-a"]
    stored = stores["test-disk-a"] / object_key(file["file_sha256"])
    assert stored.read_bytes() == b"register twice"
    assert path.exists()


def test_register_file_replaces_a_partial_copy(stores, tmp_path):
    from scene_pipelines.ingestion.files import hash_file, object_key, register_file

    path = tmp_path / "p.bin"
    path.write_bytes(b"complete bytes")
    target = stores["test-disk-a"] / object_key(hash_file(path)[0])
    target.parent.mkdir(parents=True)
    target.write_bytes(b"compl")

    register_file(path, store="test-disk-a")
    assert target.read_bytes() == b"complete bytes"


def test_remove_location_keeps_the_last_copy(stores, tmp_path):
    from scene_pipelines.ingestion.files import locations, register_file, remove_location

    path = tmp_path / "c.bin"
    path.write_bytes(b"two copies")
    file = register_file(path, store="test-disk-a")
    assert register_file(path, store="test-disk-b") == file
    assert locations(file) == ["test-disk-a", "test-disk-b"]

    remove_location(file, store="test-disk-a")
    assert locations(file) == ["test-disk-b"]
    with pytest.raises(ValueError, match="last copy"):
        remove_location(file, store="test-disk-b")


def test_record_stored_checks_the_store(stores):
    from scene_pipelines.ingestion.files import locations, object_key, record_stored

    sha = "e" * 64
    with pytest.raises(ValueError, match="no 4-byte object"):
        record_stored(sha, 4, store="test-disk-a")

    target = stores["test-disk-a"] / object_key(sha)  # copied by e.g. a transfer job
    target.parent.mkdir(parents=True)
    target.write_bytes(b"1234")
    with pytest.raises(ValueError, match="no 5-byte object"):
        record_stored(sha, 5, store="test-disk-a")
    file = record_stored(sha, 4, store="test-disk-a")
    assert locations(file) == ["test-disk-a"]


def test_same_hash_with_another_size_is_refused(stores):
    from scene_pipelines.ingestion.files import object_key, record_stored

    sha = "f" * 64
    for name, data in (("test-disk-a", b"x" * 10), ("test-disk-b", b"x" * 11)):
        target = stores[name] / object_key(sha)
        target.parent.mkdir(parents=True)
        target.write_bytes(data)

    record_stored(sha, 10, store="test-disk-a")
    with pytest.raises(ValueError, match="stored with 10 bytes"):
        record_stored(sha, 11, store="test-disk-b")


@pytest.mark.parametrize(
    ("store", "message"),
    [
        ("nowhere", "unknown store"),
        ("test-unmounted", "not mounted"),
        ("test-wrong-kind", "store_kind is not file"),
    ],
)
def test_bad_stores_are_refused(stores, tmp_path, store, message):
    from scene_pipelines.ingestion.files import register_file

    path = tmp_path / "d.bin"
    path.write_bytes(b"nowhere to go")
    with pytest.raises(ValueError, match=message):
        register_file(path, store=store)
    assert not (tmp_path / "not-mounted").exists()
