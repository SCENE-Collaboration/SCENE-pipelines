"""Unit tests for the file helpers (no database)."""

import hashlib

import pytest
from scene_pipelines.ingestion.files import hash_file, object_key, record_stored


def test_hash_file_reads_in_chunks(tmp_path):
    data = b"x" * (3 << 20) + b"tail"
    path = tmp_path / "f.bin"
    path.write_bytes(data)
    assert hash_file(path) == (hashlib.sha256(data).hexdigest(), len(data))


def test_object_key_is_derived_from_content():
    sha = "ab" + "0" * 62
    assert object_key(sha) == f"sha256/ab/{sha}"


@pytest.mark.parametrize("sha", ["abc", "g" * 64, "a" * 65])
def test_record_stored_rejects_malformed_hashes(sha):
    with pytest.raises(ValueError, match="SHA-256"):
        record_stored(sha, 1, store="any")


def test_record_stored_rejects_negative_sizes():
    with pytest.raises(ValueError, match="or size"):
        record_stored("a" * 64, -1, store="any")
