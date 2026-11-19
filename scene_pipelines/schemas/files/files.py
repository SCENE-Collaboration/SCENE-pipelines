"""SCENE-shared files: bytes kept in a store outside the database, identified by their SHA-256."""

import datajoint as dj

from scene_pipelines.core.access_markers import SyncAuthority, mark_sync_authority
from scene_pipelines.schemas.files._schema import schema

FILE_STORE = "scene-files"
"""Name of the DataJoint store that holds the bytes of every ``File``.

Each machine maps the name to a place in ``dj.config["stores"]``: the lab's file server on lab
machines, an S3 bucket on central. Every copy of the store holds a file at the same path,
``object_key(file_sha256)``, so a row reads from whichever copy the machine is configured for.
"""


def object_key(file_sha256: str) -> str:
    """Path of a file in every copy of the store, from its content: ``sha256/ab/abcd...``.

    Holds no names, so a listing of the store reveals nothing about participants, and the same
    bytes always land on the same path.
    """
    return f"sha256/{file_sha256[:2]}/{file_sha256}"


@mark_sync_authority(SyncAuthority.SHARED)
@schema
class File(dj.Manual):
    """The bytes of one file that comes from outside the pipeline, identified by content.

    For files kept byte for byte: recordings, videos, configuration files. The same bytes are
    one row everywhere, so rows are immutable and not stamped as RowMeta. What a file is (an EEG
    recording, a DLC config) belongs to the table that references ``File``. Data the pipeline
    computes does not go here: it uses DataJoint's own storage types (``<npy@>``, ``<object@>``,
    ``<blob@>``) in its own tables.

    ``content`` is DataJoint's reference to the bytes (``<filepath@scene-files>``), at
    ``object_key(file_sha256)``. On insert DataJoint checks that the file is in the store;
    fetching ``content`` returns an ``ObjectRef`` (``read()``, ``open()``, ``download()``).
    DataJoint never deletes these files.
    """

    definition = f"""
    file_sha256: char(64)  # lowercase hex SHA-256 of the bytes
    ---
    size_bytes: int64
    content: <filepath@{FILE_STORE}>  # the bytes in the store, at object_key(file_sha256)
    """
