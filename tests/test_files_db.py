"""Live-DB tests for the file helpers."""

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
def file_store(dj_connection, monkeypatch, tmp_path):
    """The ``scene-files`` store, configured as a folder on disk; returns the folder."""
    import datajoint as dj
    from scene_pipelines.ingestion.files import FILE_STORE

    root = tmp_path / "store"
    root.mkdir()
    store = {"protocol": "file", "location": str(root), "filepath_prefix": "sha256"}
    monkeypatch.setitem(dj.config, "stores", {**dict(dj.config.stores), FILE_STORE: store})
    return root


def _place(root, sha, data):
    """Put bytes in the store at the key of ``sha``, as a transfer job would."""
    from scene_pipelines.ingestion.files import object_key

    target = root / object_key(sha)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def test_register_file_copies_and_records_once(file_store, tmp_path):
    from scene_pipelines.ingestion.files import object_key, register_file
    from scene_pipelines.schemas.files.files import File

    path = tmp_path / "a.bin"
    path.write_bytes(b"register twice")
    file = register_file(path)
    assert register_file(path) == file

    assert len(File & file) == 1
    assert (file_store / object_key(file["file_sha256"])).read_bytes() == b"register twice"
    assert path.exists()


def test_content_reads_back_through_datajoint(file_store, tmp_path):
    from scene_pipelines.ingestion.files import register_file
    from scene_pipelines.schemas.files.files import File

    path = tmp_path / "r.bin"
    path.write_bytes(b"read me back")
    file = register_file(path)

    ref = (File & file).fetch1("content")
    assert ref.read() == b"read me back"
    assert ref.download(tmp_path / "downloads").read_bytes() == b"read me back"


def test_register_file_replaces_a_partial_copy(file_store, tmp_path):
    from scene_pipelines.ingestion.files import hash_file, register_file

    path = tmp_path / "p.bin"
    path.write_bytes(b"complete bytes")
    target = _place(file_store, hash_file(path)[0], b"compl")

    register_file(path)
    assert target.read_bytes() == b"complete bytes"


def test_record_file_checks_the_store(file_store):
    from scene_pipelines.ingestion.files import record_file

    sha = "e" * 64
    with pytest.raises(ValueError, match="no 4-byte file"):
        record_file(sha, 4)

    _place(file_store, sha, b"1234")
    with pytest.raises(ValueError, match="no 5-byte file"):
        record_file(sha, 5)
    file = record_file(sha, 4)
    assert record_file(sha.upper(), 4) == file


def test_same_hash_with_another_size_is_refused(file_store):
    from scene_pipelines.ingestion.files import record_file

    sha = "f" * 64
    _place(file_store, sha, b"x" * 10)
    record_file(sha, 10)

    _place(file_store, sha, b"x" * 11)
    with pytest.raises(ValueError, match="recorded with 10 bytes"):
        record_file(sha, 11)
