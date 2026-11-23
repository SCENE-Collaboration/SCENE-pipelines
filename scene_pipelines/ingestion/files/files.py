"""Register files in ``File`` and, where this deployment keeps their bytes, ``FileContent``.

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

from scene_pipelines.core.db import atomic
from scene_pipelines.core.types import DjKey
from scene_pipelines.schemas.files.files import FILE_STORE, File, FileContent, object_key

STORE_MARKER = "scene-files.json"
"""Marker file at the root of every prepared copy of the store."""

_CHUNK = 1 << 20
_SHA256 = re.compile(r"[0-9a-f]{64}")


class FileHash(NamedTuple):
    """A file's SHA-256 (hex) and size."""

    sha256: str
    size_bytes: int


def hash_file(path: str | Path) -> FileHash:
    """SHA-256 (lowercase hex) and size of a file, read in chunks."""
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as file:
        while chunk := file.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return FileHash(digest.hexdigest(), size)


def register_file(path: str | Path, *, store: bool = True) -> DjKey[File]:
    """Register a local file: store and register its bytes, or (``store=False``) its hash only.

    Args:
        path: A local file; it stays where it is.
        store: Copy the bytes into this deployment's store; ``False`` for files kept elsewhere.

    Returns:
        ``File`` key.

    Raises:
        ValueError: If ``path`` is not a file, or the store is unusable.
        DataJointError: If ``scene-files`` is not configured (when storing).
    """
    if not store:
        path = Path(path)
        if not path.is_file():
            raise ValueError(f"not a file: {path}")
        return register_file_hash(hash_file(path))
    return register_stored_file(store_file(path))


def register_file_hash(file_hash: FileHash) -> DjKey[File]:
    """Register a file by its hash only, in ``File``: its bytes stay where they are.

    Args:
        file_hash: Its SHA-256 and size.

    Returns:
        ``File`` key.

    Raises:
        ValueError: If the hash or size is malformed, or the hash is registered with another
            size.
    """
    file, size_bytes = _checked(file_hash)
    return _insert_file(file, size_bytes)


def store_file(path: str | Path) -> FileHash:
    """Copy a local file into the store unless it is there; no database write.

    Validate the file first, and store only finished files: a later change goes unnoticed
    until ``verify_file`` (datajoint-python#1745).

    Args:
        path: A local file; it stays where it is.

    Returns:
        Its ``FileHash``, for ``register_stored_file``.

    Raises:
        ValueError: If ``path`` is not a file, or the store is unusable.
        DataJointError: If ``scene-files`` is not configured.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    file_hash = hash_file(path)
    backend, key = _backend(), object_key(file_hash.sha256)
    if not _holds(backend, key, file_hash.size_bytes):
        if backend.protocol == "file" and backend.exists(key):
            backend.remove(key)  # wrong size; put_file cannot overwrite on Windows (#1744)
        backend.put_file(path, key)
    return file_hash


def register_stored_file(file_hash: FileHash) -> DjKey[File]:
    """Register bytes already in the store (by ``store_file``, or a transfer job).

    Writes ``File`` and ``FileContent`` in one transaction, or in the caller's.

    Args:
        file_hash: Their SHA-256 and size, e.g. ``FileHash(sha256, size_bytes)``.

    Returns:
        ``File`` key.

    Raises:
        ValueError: If the hash or size is malformed, the store is unusable or lacks the
            file, or the hash is registered with another size.
        DataJointError: If ``scene-files`` is not configured.
    """
    file, size_bytes = _checked(file_hash)
    key = object_key(file["file_sha256"])
    if not _holds(_backend(), key, size_bytes):
        raise ValueError(f"store {FILE_STORE!r} has no {size_bytes}-byte file at {key}")
    with atomic(File.connection):
        _insert_file(file, size_bytes)
        FileContent.insert1({**file, "content": key}, skip_duplicates=True)
    return file


def verify_file(file: DjKey[File]) -> None:
    """Re-read a file from this deployment's store and check its SHA-256 and size (an audit).

    Raises:
        ValueError: If this deployment holds no content for the file, or the bytes do not
            match the row.
        FileNotFoundError: If the file is missing from the store.
    """
    row = (File & file).fetch1()
    if not (FileContent & file):
        raise ValueError(f"no content for {row['file_sha256']} in this deployment's store")
    digest, size = hashlib.sha256(), 0
    with (FileContent & file).fetch1("content").open() as stored:
        while chunk := stored.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    if (digest.hexdigest(), size) != (row["file_sha256"], row["size_bytes"]):
        raise ValueError(
            f"store {FILE_STORE!r} holds other bytes for {row['file_sha256']}: "
            f"{size} bytes with SHA-256 {digest.hexdigest()}"
        )


def _checked(file_hash: FileHash) -> tuple[DjKey[File], int]:
    """``File`` key (lowercase hash) and size; raises on a malformed hash or size."""
    file_sha256, size_bytes = file_hash
    file = {"file_sha256": file_sha256.lower()}
    if not _SHA256.fullmatch(file["file_sha256"]) or size_bytes < 0:
        raise ValueError(f"invalid SHA-256 or size: {file_sha256!r}, {size_bytes}")
    return file, size_bytes


def _insert_file(file: DjKey[File], size_bytes: int) -> DjKey[File]:
    """Insert the ``File`` row unless present; refuses the same hash with another size."""
    File.insert1({**file, "size_bytes": size_bytes}, skip_duplicates=True)
    registered = (File & file).fetch1("size_bytes")
    if registered != size_bytes:
        raise ValueError(
            f"file {file['file_sha256']} is registered with {registered} bytes, not {size_bytes}"
        )
    return file


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
