"""Put files in the ``scene-files`` store and record them in ``File``.

Each machine configures the store in ``dj.config["stores"]`` (or ``DJ_STORES``)::

    {"scene-files": {"protocol": "file", "location": "/mnt/labserver/scene-files",
                     "filepath_prefix": "sha256"}}
    {"scene-files": {"protocol": "s3", "endpoint": "s3.example.org", "bucket": "scene",
                     "location": "scene-files", "filepath_prefix": "sha256"}}

S3 needs ``scene-pipelines[s3]``, with keys in ``.secrets/stores.scene-files.*``. Preparing,
copying and auditing a store: see Administration > File store in the docs.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import NamedTuple

import datajoint as dj
from datajoint.hash_registry import get_store_backend
from datajoint.storage import StorageBackend

from scene_pipelines.core.types import DjKey
from scene_pipelines.schemas.files.files import FILE_STORE, File, object_key

STORE_MARKER = "scene-files.json"
"""Marker file at the root of every prepared copy of the store."""

_CHUNK = 1 << 20
_SHA256 = re.compile(r"[0-9a-f]{64}")


def hash_file(path: str | Path) -> tuple[str, int]:
    """SHA-256 (lowercase hex) and size of a file, read in chunks."""
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as file:
        while chunk := file.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


class StoredFile(NamedTuple):
    """Bytes in the store: their SHA-256 (hex) and size."""

    sha256: str
    size_bytes: int


def register_file(path: str | Path) -> DjKey[File]:
    """Store a local file and register it: ``store_file``, then ``register_stored_file``.

    Args:
        path: A local file; it stays where it is.

    Returns:
        ``File`` key.

    Raises:
        ValueError: If ``path`` is not a file, or the store is unusable.
        DataJointError: If ``scene-files`` is not configured.
    """
    return register_stored_file(store_file(path))


def store_file(path: str | Path) -> StoredFile:
    """Copy a local file into the store unless it is there; no database write.

    Validate the file first, and store only finished files: a later change goes unnoticed
    until ``verify_file`` (datajoint-python#1745).

    Args:
        path: A local file; it stays where it is.

    Returns:
        Its ``StoredFile``, for ``register_stored_file``.

    Raises:
        ValueError: If ``path`` is not a file, or the store is unusable.
        DataJointError: If ``scene-files`` is not configured.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    stored = StoredFile(*hash_file(path))
    backend, key = _backend(), object_key(stored.sha256)
    if not _holds(backend, key, stored.size_bytes):
        if backend.protocol == "file" and backend.exists(key):
            backend.remove(key)  # wrong size; put_file cannot overwrite on Windows (#1744)
        backend.put_file(path, key)
    return stored


def register_stored_file(stored: StoredFile) -> DjKey[File]:
    """Register bytes already in the store (by ``store_file``, or a transfer job) in ``File``.

    Args:
        stored: Their SHA-256 and size, e.g. ``StoredFile(sha256, size_bytes)``.

    Returns:
        ``File`` key.

    Raises:
        ValueError: If the hash or size is malformed, the store is unusable or lacks the
            file, or the hash is registered with another size.
        DataJointError: If ``scene-files`` is not configured.
    """
    file_sha256, size_bytes = stored
    file = {"file_sha256": file_sha256.lower()}
    if not _SHA256.fullmatch(file["file_sha256"]) or size_bytes < 0:
        raise ValueError(f"invalid SHA-256 or size: {file_sha256!r}, {size_bytes}")
    key = object_key(file["file_sha256"])
    if not _holds(_backend(), key, size_bytes):
        raise ValueError(f"store {FILE_STORE!r} has no {size_bytes}-byte file at {key}")
    File.insert1({**file, "size_bytes": size_bytes, "content": key}, skip_duplicates=True)
    stored_size = (File & file).proj("size_bytes").fetch1()["size_bytes"]
    if stored_size != size_bytes:
        raise ValueError(
            f"file {file['file_sha256']} is registered with {stored_size} bytes, not {size_bytes}"
        )
    return file


def verify_file(file: DjKey[File]) -> None:
    """Re-read a file from the store and check its SHA-256 and size (an occasional audit).

    Raises:
        ValueError: If the bytes do not match the row.
        FileNotFoundError: If the file is missing from the store.
    """
    row = (File & file).proj("size_bytes").fetch1()
    digest, size = hashlib.sha256(), 0
    with (File & file).fetch1("content").open() as stored:
        while chunk := stored.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    if (digest.hexdigest(), size) != (row["file_sha256"], row["size_bytes"]):
        raise ValueError(
            f"store {FILE_STORE!r} holds other bytes for {row['file_sha256']}: "
            f"{size} bytes with SHA-256 {digest.hexdigest()}"
        )


def _backend() -> StorageBackend:
    """Backend of the ``scene-files`` store; refuses an unmounted or unprepared one."""
    spec = dj.config.get_store_spec(FILE_STORE)
    if spec["protocol"] == "file" and not Path(spec["location"]).is_dir():
        raise ValueError(f"store {FILE_STORE!r} is not mounted at {spec['location']}")
    backend = get_store_backend(FILE_STORE)
    if not backend.exists(STORE_MARKER):
        raise ValueError(
            f"store {FILE_STORE!r} has no {STORE_MARKER} at {spec['location']}: not mounted, "
            "wrong location, or not prepared with admin.init_file_store()"
        )
    return backend


def _holds(backend: StorageBackend, key: str, size_bytes: int) -> bool:
    """Whether the store has a file of ``size_bytes`` at ``key``."""
    return backend.exists(key) and backend.size(key) == size_bytes
