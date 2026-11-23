"""SCENE-shared files: bytes kept in a store outside the database, identified by their SHA-256."""

import datajoint as dj

from scene_pipelines.core.access_markers import SyncAuthority, mark_sync_authority
from scene_pipelines.schemas.files._schema import schema

FILE_STORE = "scene-files"
"""DataJoint store with the bytes of every ``File``; each machine maps it in ``dj.config``."""


def object_key(file_sha256: str) -> str:
    """Path of a file in every copy of the store, from its content only: ``sha256/ab/abcd...``."""
    return f"sha256/{file_sha256[:2]}/{file_sha256}"


@mark_sync_authority(SyncAuthority.SHARED)
@schema
class File(dj.Manual):
    """One file from outside the pipeline (recording, video, config), identified by SHA-256.

    Immutable and the same everywhere, so not stamped as RowMeta. What the file is belongs to
    the table referencing it; computed data uses DataJoint's own storage types instead.
    ``content`` fetches as an ``ObjectRef`` (``read()``, ``open()``, ``download()``).
    """

    definition = f"""
    file_sha256: char(64)  # lowercase hex SHA-256 of the bytes
    ---
    size_bytes: int64
    content: <filepath@{FILE_STORE}>  # the bytes in the store, at object_key(file_sha256)
    """
