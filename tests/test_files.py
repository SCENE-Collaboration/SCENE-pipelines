"""Unit tests for the file helpers (no database)."""

import hashlib

from scene_pipelines.core import load_settings
from scene_pipelines.ingestion.files import hash_file, object_key
from scene_pipelines.ingestion.files.files import _copy_into


def test_hash_file_reads_in_chunks(tmp_path):
    data = b"x" * (3 << 20) + b"tail"
    path = tmp_path / "f.bin"
    path.write_bytes(data)
    assert hash_file(path) == (hashlib.sha256(data).hexdigest(), len(data))


def test_object_key_is_derived_from_content():
    sha = "ab" + "0" * 62
    assert object_key(sha) == f"sha256/ab/{sha}"


def test_copy_into_places_the_bytes_at_their_key_once(tmp_path):
    source = tmp_path / "P012 video.mp4"
    source.write_bytes(b"frames")
    root = tmp_path / "store"
    sha, size = _copy_into(source, root)

    assert (sha, size) == (hashlib.sha256(b"frames").hexdigest(), 6)
    assert (root / object_key(sha)).read_bytes() == b"frames"
    assert _copy_into(source, root) == (sha, size)
    assert [p.name for p in root.rglob("*") if p.is_file()] == [sha]
    assert source.exists()


def test_store_setting(monkeypatch):
    monkeypatch.delenv("SCENE_STORE", raising=False)
    assert load_settings().store is None
    monkeypatch.setenv("SCENE_STORE", " kccl-raw ")
    assert load_settings().store == "kccl-raw"
