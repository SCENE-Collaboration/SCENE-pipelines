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


def _configure(monkeypatch, root):
    """Point the ``scene-files`` store at the folder ``root``."""
    import datajoint as dj
    from scene_pipelines.ingestion.files import FILE_STORE

    store = {"protocol": "file", "location": str(root), "filepath_prefix": "sha256"}
    monkeypatch.setitem(dj.config, "stores", {**dict(dj.config.stores), FILE_STORE: store})


@pytest.fixture
def file_store(dj_connection, monkeypatch, tmp_path):
    """A prepared ``scene-files`` store on disk; returns its folder."""
    from scene_pipelines.ingestion.files.admin import init_file_store

    root = tmp_path / "store"
    root.mkdir()
    _configure(monkeypatch, root)
    init_file_store(new_copy=True)  # other tests' files are recorded
    return root


def _place(root, sha, data):
    """Put bytes at the key of ``sha``, as a transfer job would."""
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


def test_init_file_store_refuses_a_place_without_the_recorded_files(
    file_store, monkeypatch, tmp_path
):
    from scene_pipelines.ingestion.files import STORE_MARKER, register_file
    from scene_pipelines.ingestion.files.admin import init_file_store

    path = tmp_path / "known.bin"
    path.write_bytes(b"recorded in the database")
    register_file(path)

    elsewhere = tmp_path / "mount-point"  # empty: disk not mounted
    elsewhere.mkdir()
    _configure(monkeypatch, elsewhere)
    with pytest.raises(ValueError, match="holds none of the files"):
        init_file_store()
    assert not (elsewhere / STORE_MARKER).exists()


def test_register_stored_file_checks_the_store(file_store):
    from scene_pipelines.ingestion.files import StoredFile, register_stored_file

    sha = "e" * 64
    with pytest.raises(ValueError, match="no 4-byte file"):
        register_stored_file(StoredFile(sha, 4))

    _place(file_store, sha, b"1234")
    with pytest.raises(ValueError, match="no 5-byte file"):
        register_stored_file(StoredFile(sha, 5))
    file = register_stored_file(StoredFile(sha, 4))
    assert register_stored_file(StoredFile(sha.upper(), 4)) == file


def test_same_hash_with_another_size_is_refused(file_store):
    from scene_pipelines.ingestion.files import StoredFile, register_stored_file

    sha = "f" * 64
    _place(file_store, sha, b"x" * 10)
    register_stored_file(StoredFile(sha, 10))

    _place(file_store, sha, b"x" * 11)
    with pytest.raises(ValueError, match="registered with 10 bytes"):
        register_stored_file(StoredFile(sha, 11))


def test_registration_joins_the_callers_transaction(file_store, tmp_path):
    from scene_pipelines.ingestion.files import register_stored_file, store_file
    from scene_pipelines.schemas.files.files import File

    path = tmp_path / "t.bin"
    path.write_bytes(b"stored, then registered with its modality row")
    stored = store_file(path)
    with pytest.raises(RuntimeError), File.connection.transaction:
        register_stored_file(stored)
        raise RuntimeError("the modality row failed")
    assert not (File & {"file_sha256": stored.sha256})

    assert register_stored_file(stored) == {"file_sha256": stored.sha256}


def test_verify_file_detects_changed_bytes(file_store, tmp_path):
    from scene_pipelines.ingestion.files import object_key, register_file, verify_file

    path = tmp_path / "v.bin"
    path.write_bytes(b"original")
    file = register_file(path)
    verify_file(file)

    (file_store / object_key(file["file_sha256"])).write_bytes(b"tampered")  # same size
    with pytest.raises(ValueError, match="other bytes"):
        verify_file(file)
