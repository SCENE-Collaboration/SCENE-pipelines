"""Put files in the ``scene-files`` store and record them in ``File``.

``register_file`` copies a local file into the store with DataJoint's storage backend and
records it. A transfer job (e.g. rclone) may copy instead; ``record_file`` then records what it
put there. Either way the bytes are in the store before their row.

Each machine that reads or writes files configures the store under its name, ``scene-files``,
next to the database connection (``datajoint.json``, ``DJ_STORES`` or ``dj.config``)::

    {"stores": {"scene-files": {"protocol": "file", "location": "/mnt/labserver/scene-files",
                                "filepath_prefix": "sha256"}}}

    {"stores": {"scene-files": {"protocol": "s3", "endpoint": "s3.example.org",
                                "bucket": "scene", "location": "scene-files",
                                "filepath_prefix": "sha256"}}}

S3 keys go in ``.secrets/stores.scene-files.access_key`` and ``...secret_key``, never in the
database; S3 needs ``s3fs`` (``pip install "scene-pipelines[s3]"``). ``filepath_prefix`` makes
DataJoint refuse any path outside ``sha256/``.

Every copy of the store holds a file at ``object_key(file_sha256)``, so copies can be kept in
step with ``rclone copy --checksum`` (``copy``, not ``sync``: these files are never deleted).
A database that receives ``File`` rows from another one (sync) reads them from its own copy,
so the bytes must reach that copy before the rows do.

Fetch the bytes with DataJoint: ``(File & key).fetch1("content")`` returns an ``ObjectRef``
with ``read()``, ``open()`` and ``download(folder)``.
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
    """Copy a local file into the store unless it is there, and record it in ``File``.

    The file is hashed first, then copied with DataJoint's storage backend (on disk: to a
    temporary file, then renamed). The original stays where it is. Registering the same bytes
    again copies nothing and returns the same key.

    Args:
        path: A local file.

    Returns:
        ``File`` primary key ``{"file_sha256": ...}``.

    Raises:
        ValueError: If ``path`` is not a file, or the store is on disk and not mounted.
        DataJointError: If ``scene-files`` is not configured in ``dj.config["stores"]``.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    file_sha256, size_bytes = hash_file(path)
    backend, key = _backend(), object_key(file_sha256)
    if not _holds(backend, key, size_bytes):
        if backend.exists(key):
            backend.remove(key)  # a partial copy; the rename below cannot replace it on Windows
        backend.put_file(path, key)
    return record_file(file_sha256, size_bytes)


def record_file(file_sha256: str, size_bytes: int) -> DjKey[File]:
    """Record bytes that are already in the store at ``object_key(file_sha256)``.

    For a transfer job that has put the bytes there and checked them, e.g. with
    ``rclone copy --checksum``. Checks that the store holds a file of ``size_bytes`` at the
    key; recording the same bytes again does nothing.

    Args:
        file_sha256: SHA-256 of the bytes, hex.
        size_bytes: Their size.

    Returns:
        ``File`` primary key ``{"file_sha256": ...}``.

    Raises:
        ValueError: If the hash or size is malformed, the store holds no file of that size
            at the key, or the hash is recorded with another size.
        DataJointError: If ``scene-files`` is not configured in ``dj.config["stores"]``.
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
    """Read a file back from the store and check its SHA-256 and size against its row.

    Reads the whole file, in chunks: an audit to run now and then, not a step of every write.

    Args:
        file: ``File`` primary key.

    Raises:
        ValueError: If the bytes in the store do not match the row.
        FileNotFoundError: If the store has no file at the row's path.
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
    """DataJoint's backend for the ``scene-files`` store; a store on disk must be mounted."""
    spec = dj.config.get_store_spec(FILE_STORE)
    if spec["protocol"] == "file" and not Path(spec["location"]).is_dir():
        raise ValueError(f"store {FILE_STORE!r} is not mounted at {spec['location']}")
    return get_store_backend(FILE_STORE)


def _holds(backend: StorageBackend, key: str, size_bytes: int) -> bool:
    """Whether the store has a file of ``size_bytes`` at ``key``."""
    return backend.exists(key) and backend.size(key) == size_bytes
