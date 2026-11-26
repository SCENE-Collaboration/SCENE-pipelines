"""Unit tests for the file helpers (no database)."""

import hashlib
import json
import os
import stat
import sys

import datajoint as dj
import pytest
from datajoint.storage import StorageBackend
from scene_pipelines.ingestion.files import (
    FILE_STORE,
    STORE_MARKER,
    FileHash,
    admin,
    hash_file,
    object_key,
    register_file,
    register_file_hash,
    register_stored_file,
    store_file,
)
from scene_pipelines.schemas.files.files import File, FileContent


def _disk_store(monkeypatch, root):
    """Configure ``scene-files`` as the folder ``root``."""
    monkeypatch.setitem(
        dj.config, "stores", {FILE_STORE: {"protocol": "file", "location": str(root)}}
    )


def _recorded(monkeypatch, *shas):
    """Fake the files the database records."""
    monkeypatch.setattr(admin, "_some_recorded_files", lambda: list(shas))


def test_hash_file_reads_in_chunks(tmp_path):
    data = b"x" * (3 << 20) + b"tail"
    path = tmp_path / "f.bin"
    path.write_bytes(data)
    assert hash_file(path) == (hashlib.sha256(data).hexdigest(), len(data))


def test_object_key_is_derived_from_content():
    sha = "ab" + "0" * 62
    assert object_key(sha) == f"sha256/ab/{sha}"


def test_only_file_content_references_the_store():
    assert "<filepath@" not in File.definition
    assert f"<filepath@{FILE_STORE}>" in FileContent.definition


_REGISTER = [register_file_hash, register_stored_file]


@pytest.mark.parametrize("register", _REGISTER)
@pytest.mark.parametrize("sha", ["abc", "g" * 64, "a" * 65])
def test_registration_rejects_malformed_hashes(register, sha):
    with pytest.raises(ValueError, match="SHA-256"):
        register(FileHash(sha, 1))


@pytest.mark.parametrize("register", _REGISTER)
def test_registration_rejects_negative_sizes(register):
    with pytest.raises(ValueError, match="or size"):
        register(FileHash("a" * 64, -1))


def test_register_file_by_hash_refuses_a_folder(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        register_file(tmp_path, store=False)


def test_store_file_copies_without_the_database(monkeypatch, tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    _disk_store(monkeypatch, store)
    _recorded(monkeypatch)
    admin.init_file_store()
    path = tmp_path / "a.bin"
    path.write_bytes(b"stored only")

    stored = store_file(path)
    assert stored == hash_file(path)
    assert (store / object_key(stored.sha256)).read_bytes() == b"stored only"


@pytest.mark.xfail(
    sys.platform == "win32", strict=True, reason="datajoint-python#1744: no overwrite on Windows"
)
def test_datajoint_put_file_overwrites(tmp_path):
    """Once this passes on Windows, drop the remove() before put_file in store_file."""
    store = tmp_path / "store"
    (store / "x").mkdir(parents=True)
    (store / "x" / "a.bin").write_bytes(b"old")
    source = tmp_path / "a.bin"
    source.write_bytes(b"new")
    StorageBackend({"protocol": "file", "location": str(store)}).put_file(source, "x/a.bin")
    assert (store / "x" / "a.bin").read_bytes() == b"new"


def test_register_file_refuses_a_folder(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        register_file(tmp_path)


def test_register_file_refuses_an_unmounted_store(monkeypatch, tmp_path):
    unmounted = tmp_path / "not-mounted"
    _disk_store(monkeypatch, unmounted)
    path = tmp_path / "a.bin"
    path.write_bytes(b"nowhere to go")
    with pytest.raises(ValueError, match="not mounted"):
        register_file(path)
    assert not unmounted.exists()


def test_register_file_refuses_a_store_without_its_marker(monkeypatch, tmp_path):
    mount_point = tmp_path / "mount-point"  # empty: disk not mounted
    mount_point.mkdir()
    _disk_store(monkeypatch, mount_point)
    path = tmp_path / "a.bin"
    path.write_bytes(b"nowhere to go")
    with pytest.raises(ValueError, match=STORE_MARKER):
        register_file(path)
    assert not any(mount_point.iterdir())


def test_register_file_needs_the_store_configured(monkeypatch, tmp_path):
    monkeypatch.setitem(dj.config, "stores", {})
    path = tmp_path / "a.bin"
    path.write_bytes(b"no store")
    with pytest.raises(dj.DataJointError, match=FILE_STORE):
        register_file(path)


def test_init_file_store_writes_the_marker(monkeypatch, tmp_path):
    _disk_store(monkeypatch, tmp_path)
    _recorded(monkeypatch)
    admin.init_file_store()
    assert json.loads((tmp_path / STORE_MARKER).read_text())["store"] == FILE_STORE


def test_init_file_store_creates_the_shared_folders(monkeypatch, tmp_path):
    _disk_store(monkeypatch, tmp_path)
    _recorded(monkeypatch)
    admin.init_file_store()
    folders = sorted(folder.name for folder in (tmp_path / "sha256").iterdir())
    assert folders == [f"{i:02x}" for i in range(256)]
    if os.name == "posix":
        assert stat.S_IMODE((tmp_path / "sha256" / "ab").stat().st_mode) == 0o2775


def test_init_file_store_runs_only_once(monkeypatch, tmp_path):
    _disk_store(monkeypatch, tmp_path)
    _recorded(monkeypatch)
    admin.init_file_store()
    with pytest.raises(ValueError, match="already prepared"):
        admin.init_file_store()


def test_init_file_store_refuses_a_place_without_the_recorded_files(monkeypatch, tmp_path):
    _disk_store(monkeypatch, tmp_path)  # empty: disk not mounted
    _recorded(monkeypatch, "a" * 64, "b" * 64)
    with pytest.raises(ValueError, match="new_copy=True"):
        admin.init_file_store()
    assert not (tmp_path / STORE_MARKER).exists()

    admin.init_file_store(new_copy=True)
    assert (tmp_path / STORE_MARKER).exists()


def test_init_file_store_accepts_a_place_with_a_recorded_file(monkeypatch, tmp_path):
    _disk_store(monkeypatch, tmp_path)
    _recorded(monkeypatch, "a" * 64, "b" * 64)
    held = tmp_path / object_key("b" * 64)
    held.parent.mkdir(parents=True)
    held.write_bytes(b"bytes")
    admin.init_file_store()
    assert (tmp_path / STORE_MARKER).exists()


def test_init_file_store_refuses_a_missing_folder(monkeypatch, tmp_path):
    _disk_store(monkeypatch, tmp_path / "missing")
    with pytest.raises(ValueError, match="create it only for a new store"):
        admin.init_file_store()
    assert not (tmp_path / "missing").exists()
