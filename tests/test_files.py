"""Unit tests for the file helpers (no database)."""

import hashlib

import datajoint as dj
import pytest
from scene_pipelines.ingestion.files import (
    FILE_STORE,
    hash_file,
    object_key,
    record_file,
    register_file,
)
from scene_pipelines.schemas.files.files import File


def test_hash_file_reads_in_chunks(tmp_path):
    data = b"x" * (3 << 20) + b"tail"
    path = tmp_path / "f.bin"
    path.write_bytes(data)
    assert hash_file(path) == (hashlib.sha256(data).hexdigest(), len(data))


def test_object_key_is_derived_from_content():
    sha = "ab" + "0" * 62
    assert object_key(sha) == f"sha256/ab/{sha}"


def test_file_content_is_a_reference_into_the_file_store():
    assert f"<filepath@{FILE_STORE}>" in File.definition


@pytest.mark.parametrize("sha", ["abc", "g" * 64, "a" * 65])
def test_record_file_rejects_malformed_hashes(sha):
    with pytest.raises(ValueError, match="SHA-256"):
        record_file(sha, 1)


def test_record_file_rejects_negative_sizes():
    with pytest.raises(ValueError, match="or size"):
        record_file("a" * 64, -1)


def test_register_file_refuses_a_folder(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        register_file(tmp_path)


def test_register_file_refuses_an_unmounted_store(monkeypatch, tmp_path):
    unmounted = tmp_path / "not-mounted"
    monkeypatch.setitem(
        dj.config, "stores", {FILE_STORE: {"protocol": "file", "location": str(unmounted)}}
    )
    path = tmp_path / "a.bin"
    path.write_bytes(b"nowhere to go")
    with pytest.raises(ValueError, match="not mounted"):
        register_file(path)
    assert not unmounted.exists()


def test_register_file_needs_the_store_configured(monkeypatch, tmp_path):
    monkeypatch.setitem(dj.config, "stores", {})
    path = tmp_path / "a.bin"
    path.write_bytes(b"no store")
    with pytest.raises(dj.DataJointError, match=FILE_STORE):
        register_file(path)
