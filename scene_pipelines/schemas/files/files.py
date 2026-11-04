"""SCENE-shared file catalogue: stores, file contents, and where copies are now."""

import datajoint as dj

from scene_pipelines.core.access_markers import (
    SyncAuthority,
    WriteRole,
    mark_sync_authority,
    mark_write_role,
)
from scene_pipelines.schemas.files._schema import schema
from scene_pipelines.schemas.scene.lab import Lab  # noqa: F401  # FK: Store -> Lab


@mark_sync_authority(SyncAuthority.CENTRAL)
@mark_write_role(WriteRole.ADMIN)
@schema
class Store(dj.Manual):
    """Admin-only insertion: managed storage where file bytes are kept (a lab server, an S3 bucket).

    A few per lab; rigs and laptops are not stores. Files are kept at ``object_key(sha256)``.

    ``store_name`` is also the name under ``dj.config["stores"]`` on each machine
    that uses it; connection details and credentials stay there, never in the database.
    The file helpers check that ``store_kind`` matches the configured ``protocol``.
    """

    definition = """
    store_name: varchar(32)  # e.g. mlai-raw — never renamed
    ---
    store_kind: enum('s3', 'file')
    -> [nullable] Lab  # lab that runs it; null: central
    store_details='': varchar(255)
    """


@mark_sync_authority(SyncAuthority.SHARED)
@schema
class File(dj.Manual):
    """The bytes of one file, identified by content: the same bytes are one row everywhere.

    Immutable and not stamped as RowMeta. Copies are in ``Location``; The names and roles (e.g.
    EEG recording file, DLC config file) are defined in the downstream table referencing ``File``.

    For raw data acquired once and shared across labs. Derived, recomputable
    results use DataJoint's own object storage instead (``<blob@store>``,
    ``<attach@store>``, ``<object@store>``), which DataJoint manages and
    garbage-collects itself.
    """

    definition = """
    file_sha256: char(64)  # lowercase hex SHA-256 of the bytes
    ---
    size_bytes: int64
    """


@schema
class Location(dj.Manual):
    """A copy of a file in a store, at ``object_key(file_sha256)``; it exists while the copy does.

    Each store has one writer: the lab's ingestion for a lab store, or central for a
    central store (``Store.lab_id`` null). That writer is the row's origin, so
    syncing a store's rows never conflicts. No write-role marker, so central can
    record copies in its own stores.

    The file helpers record a ``File`` together with its first ``Location`` and
    refuse to remove the last one. That is a convention, not a database
    constraint: a site also holds ``File`` rows whose copies are recorded elsewhere.
    """

    definition = """
    -> File
    -> Store
    """
