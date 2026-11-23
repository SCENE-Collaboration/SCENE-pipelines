"""Put files in the ``scene-files`` store and record them in ``File``.

Each machine configures the store in ``dj.config["stores"]`` (or ``DJ_STORES``)::

    {"scene-files": {"protocol": "file", "location": "/mnt/labserver/scene-files",
                     "filepath_prefix": "sha256"}}
    {"scene-files": {"protocol": "s3", "endpoint": "s3.example.org", "bucket": "scene",
                     "location": "scene-files", "filepath_prefix": "sha256"}}

S3 needs ``scene-pipelines[s3]``, with keys in ``.secrets/stores.scene-files.*``. Each copy of
the store is prepared once with ``admin.init_file_store()``. Mount a disk share above the
store's folder, so that an unmounted share has no such folder. Keep copies in step with
``rclone copy --checksum`` (never ``sync``), bytes before rows.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

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


def register_file(path: str | Path) -> DjKey[File]:
    """Copy a local file into the store unless it is there, and record it.

    Args:
        path: A local file; it stays where it is.

    Returns:
        ``File`` key.

    Raises:
        ValueError: If ``path`` is not a file, or the store is unusable.
        DataJointError: If ``scene-files`` is not configured.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    file_sha256, size_bytes = hash_file(path)
    backend, key = _backend(), object_key(file_sha256)
    if not _holds(backend, key, size_bytes):
        if backend.exists(key):
            backend.remove(key)  # wrong size; on Windows the rename cannot overwrite it
        backend.put_file(path, key)
    return record_file(file_sha256, size_bytes)


def record_file(file_sha256: str, size_bytes: int) -> DjKey[File]:
    """Record bytes already at ``object_key(file_sha256)``, e.g. copied there by rclone.

    Args:
        file_sha256: SHA-256 of the bytes, hex.
        size_bytes: Their size.

    Returns:
        ``File`` key.

    Raises:
        ValueError: If the hash or size is malformed, the store is unusable or lacks the
            file, or the hash is recorded with another size.
        DataJointError: If ``scene-files`` is not configured.
    """
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
            f"file {file['file_sha256']} is recorded with {stored_size} bytes, not {size_bytes}"
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
