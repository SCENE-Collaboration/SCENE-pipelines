"""Record files and where their copies are (everyday pipeline writes).

``register_file`` copies a file into a store with DataJoint's storage backend and
records it. A transfer job (e.g. rclone) may copy instead and call ``record_stored``.
Bytes are written before their row; a row is removed before its bytes.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import datajoint as dj
from datajoint.storage import StorageBackend

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.db import atomic
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.files._version import FILES_WRITER_VERSION
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.schemas.files.files import File, Location, Store
from scene_pipelines.schemas.files.row_meta import LocationRowMeta
from scene_pipelines.schemas.provenance.deployment import Deployment

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


def object_key(file_sha256: str) -> str:
    """Key of a file in every store, from its content: ``sha256/ab/abcd...``.

    Holds no names, so store listings reveal nothing about participants, and the
    same bytes always land on the same key.
    """
    return f"sha256/{file_sha256[:2]}/{file_sha256}"


def _store_key(store: str) -> DjKey[Store]:
    if not (Store & {"store_name": store}):
        raise ValueError(f"unknown store {store!r}; an admin registers it with ensure_store")
    return {"store_name": store}


def _backend(store_key: DjKey[Store]) -> StorageBackend:
    """DataJoint's backend for a store, checked against its ``Store`` row."""
    spec = dj.config.get_store_spec(store_key["store_name"])
    if spec["protocol"] != (Store & store_key).fetch1("store_kind"):
        raise ValueError(f"store {store_key['store_name']!r}: store_kind is not {spec['protocol']}")
    if spec["protocol"] == "file" and not Path(spec["location"]).is_dir():
        raise ValueError(f"store {store_key['store_name']!r} is not mounted at {spec['location']}")
    return StorageBackend(spec)


def _lock(file: DjKey[File]) -> tuple | None:
    """Lock the ``File`` row until the transaction ends; return ``(size_bytes,)``."""
    return File.connection.query(
        f"SELECT size_bytes FROM {File().full_table_name} WHERE file_sha256 = %s FOR UPDATE",
        args=(file["file_sha256"],),
    ).fetchone()


def _copy_into(path: Path, backend: StorageBackend) -> tuple[str, int]:
    """Copy ``path`` to ``object_key`` in a store unless it is there; return its hash and size."""
    file_sha256, size = hash_file(path)
    key = object_key(file_sha256)
    if not (backend.exists(key) and backend.size(key) == size):
        backend.remove(key)  # a partial copy, if any
        backend.put_file(path, key)  # on disk: temp file, then rename
    return file_sha256, size


def record_stored(
    file_sha256: str,
    size_bytes: int,
    *,
    store: str,
    deployment: DjRow[Deployment] | None = None,
) -> DjKey[File]:
    """Record that ``store`` holds the bytes ``file_sha256`` at ``object_key(file_sha256)``.

    For a caller that has put the bytes there and checked them; checks that the
    object is there with ``size_bytes``. Recording a stored copy again does
    nothing. Runs atomically; joins the caller's transaction when one is open.

    Args:
        file_sha256: Lowercase hex SHA-256 of the bytes.
        size_bytes: Their size.
        store: Registered store name.
        deployment: Optional deployment row; default from ``SCENE_DEPLOYMENT_ID``.

    Returns:
        File primary key ``{file_sha256: ...}``.

    Raises:
        ValueError: If the hash or size is invalid, the store is not registered,
            does not hold the object with that size, or the hash is stored with
            another size.
    """
    file = {"file_sha256": file_sha256.lower()}
    if not _SHA256.fullmatch(file["file_sha256"]) or size_bytes < 0:
        raise ValueError(f"invalid SHA-256 or size: {file_sha256!r}, {size_bytes}")
    with atomic(File.connection):
        store_key = _store_key(store)
        backend, key = _backend(store_key), object_key(file["file_sha256"])
        if not (backend.exists(key) and backend.size(key) == size_bytes):
            raise ValueError(f"store {store!r} has no {size_bytes}-byte object at {key}")
        File.insert1({**file, "size_bytes": size_bytes}, skip_duplicates=True)
        if (stored_size := _lock(file)[0]) != size_bytes:
            raise ValueError(
                f"file {file_sha256} is stored with {stored_size} bytes, not {size_bytes}"
            )
        insert_tracked_row(
            LocationRowMeta,
            {**file, **store_key},
            payload={},
            deployment=deployment if deployment is not None else deployment_row_from_settings(),
            if_exists=DuplicatePolicy.SKIP,
            writer_version=FILES_WRITER_VERSION,
        )
        return file


def register_file(
    path: str | Path,
    *,
    store: str,
    deployment: DjRow[Deployment] | None = None,
) -> DjKey[File]:
    """Copy a file into a store at ``object_key`` and record it; see ``record_stored``.

    The file is hashed, then copied unless the store holds it, before any database write.
    The original stays where it is.

    Raises:
        ValueError: If ``store_kind`` does not match ``dj.config["stores"]``, or a
            disk store is not mounted.
    """
    store_key = _store_key(store)
    file_sha256, size_bytes = _copy_into(Path(path), _backend(store_key))
    return record_stored(
        file_sha256, size_bytes, store=store_key["store_name"], deployment=deployment
    )


def locations(file: DjKey[File]) -> list[str]:
    """Names of the stores that hold a copy of ``file``; the key in each is ``object_key``."""
    return sorted(str(name) for name in (Location & file).to_arrays("store_name"))


def remove_location(file: DjKey[File], *, store: str) -> None:
    """Remove the record of a copy; delete its bytes afterwards.

    Locks the ``File`` row, so concurrent removals cannot both pass the last-copy check.

    Raises:
        ValueError: If ``store`` holds no copy, or holds the last one.
    """
    with atomic(Location.connection):
        key = {**file, **_store_key(store)}
        _lock(file)
        if not (Location & key):
            raise ValueError(f"store {key['store_name']!r} holds no copy of {file['file_sha256']}")
        if len(Location & file) == 1:
            raise ValueError(
                f"store {key['store_name']!r} holds the last copy of {file['file_sha256']}"
            )
        (LocationRowMeta & key).delete_quick()
        (Location & key).delete_quick()
