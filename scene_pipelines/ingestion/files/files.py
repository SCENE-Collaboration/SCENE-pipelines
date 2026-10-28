"""Record files and where their copies are (everyday pipeline writes).

``register_file`` copies a file into a disk store and records it. Copies into an
S3 store are made by a transfer job, which records them with ``record_stored``.
Bytes are written before their row; a row is removed before its bytes.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import datajoint as dj

from scene_pipelines.core.config import deployment_row_from_settings, load_settings
from scene_pipelines.core.db import atomic
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.files._version import FILES_WRITER_VERSION
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.schemas.files.files import File, Location, Store
from scene_pipelines.schemas.files.row_meta import LocationRowMeta
from scene_pipelines.schemas.provenance.deployment import Deployment

_CHUNK = 1 << 20


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


def _store_key(store: str | None) -> DjKey[Store]:
    name = store or load_settings().store
    if name is None:
        raise ValueError("store is required: pass store=... or set SCENE_STORE")
    if not (Store & {"store_name": name}):
        raise ValueError(f"unknown store {name!r}; an admin registers it with ensure_store")
    return {"store_name": name}


def _copy_into(path: Path, root: Path) -> tuple[str, int]:
    """Copy ``path`` to ``root / object_key`` while hashing it; return its hash and size."""
    root.mkdir(parents=True, exist_ok=True)
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as source, tempfile.NamedTemporaryFile(dir=root, delete=False) as temp:
        while chunk := source.read(_CHUNK):
            digest.update(chunk)
            temp.write(chunk)
            size += len(chunk)
    file_sha256 = digest.hexdigest()
    target = root / object_key(file_sha256)
    if target.exists():
        os.remove(temp.name)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(temp.name, target)
    return file_sha256, size


def record_stored(
    file_sha256: str,
    size_bytes: int,
    *,
    store: str | None = None,
    deployment: DjRow[Deployment] | None = None,
) -> DjKey[File]:
    """Record that ``store`` holds the bytes ``file_sha256`` at ``object_key(file_sha256)``.

    For a caller that has put the bytes there and checked them. Recording a
    stored copy again does nothing. Runs atomically; joins the caller's
    transaction when one is open.

    Args:
        file_sha256: Lowercase hex SHA-256 of the bytes.
        size_bytes: Their size.
        store: Registered store name; default ``SCENE_STORE``.
        deployment: Optional deployment row; default from ``SCENE_DEPLOYMENT_ID``.

    Returns:
        File primary key ``{file_sha256: ...}``.

    Raises:
        ValueError: If no store is given or set, the store is not registered,
            or the hash is stored with another size.
    """
    file = {"file_sha256": file_sha256.lower()}
    with atomic(File.connection):
        store_key = _store_key(store)
        stored = File & file
        if not stored:
            File.insert1({**file, "size_bytes": size_bytes})
        elif (stored_size := stored.fetch1("size_bytes")) != size_bytes:
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
    store: str | None = None,
    deployment: DjRow[Deployment] | None = None,
) -> DjKey[File]:
    """Copy a file into a disk store at ``object_key`` and record it; see ``record_stored``.

    The file is read once, hashed while it is copied, before any database write.
    The original stays where it is.

    Raises:
        ValueError: If the store is not a disk store (``file`` in ``dj.config["stores"]``).
    """
    store_key = _store_key(store)
    spec = dj.config.get_store_spec(store_key["store_name"])
    if spec["protocol"] != "file":
        raise ValueError(
            f"store {store_key['store_name']!r} is {spec['protocol']}; register_file copies into "
            "disk stores only, a transfer job uploads and calls record_stored"
        )
    file_sha256, size_bytes = _copy_into(Path(path), Path(spec["location"]))
    return record_stored(
        file_sha256, size_bytes, store=store_key["store_name"], deployment=deployment
    )


def locations(file: DjKey[File]) -> list[str]:
    """Names of the stores that hold a copy of ``file``; the key in each is ``object_key``."""
    return sorted(str(name) for name in (Location & file).to_arrays("store_name"))


def remove_location(file: DjKey[File], *, store: str | None = None) -> None:
    """Remove the record of a copy; delete its bytes afterwards.

    Raises:
        ValueError: If ``store`` holds no copy, or holds the last one.
    """
    with atomic(Location.connection):
        key = {**file, **_store_key(store)}
        if not (Location & key):
            raise ValueError(f"store {key['store_name']!r} holds no copy of {file['file_sha256']}")
        if len(Location & file) == 1:
            raise ValueError(
                f"store {key['store_name']!r} holds the last copy of {file['file_sha256']}"
            )
        (LocationRowMeta & key).delete_quick()
        (Location & key).delete_quick()
