"""Admin helper: prepare a copy of the ``scene-files`` store, once and by hand."""

from __future__ import annotations

import json
from pathlib import Path

import datajoint as dj
from datajoint.hash_registry import get_store_backend

from scene_pipelines.ingestion.files.files import STORE_MARKER
from scene_pipelines.schemas.files.files import FILE_STORE, File, object_key

_SAMPLE = 5
_MARKER_CONTENT = json.dumps(
    {
        "store": FILE_STORE,
        "layout": "sha256/<first two hex digits>/<SHA-256 of the bytes>",
        "note": "Bytes of SCENE File rows: never rename or delete.",
    },
    indent=2,
).encode()


def init_file_store(*, new_copy: bool = False) -> None:
    """Write the store marker, so the write helpers accept this machine's copy of the store.

    Args:
        new_copy: Accept a place holding none of the recorded files: a new copy to fill.

    Raises:
        ValueError: If the location is missing, already prepared, or (without ``new_copy``)
            holds none of a few files the database records.
        DataJointError: If ``scene-files`` is not configured.
    """
    spec = dj.config.get_store_spec(FILE_STORE)
    location = spec["location"]
    if spec["protocol"] == "file" and not Path(location).is_dir():
        raise ValueError(f"store {FILE_STORE!r}: mount {location}; create it only for a new store")
    backend = get_store_backend(FILE_STORE)
    if backend.exists(STORE_MARKER):
        raise ValueError(f"store {FILE_STORE!r} at {location} is already prepared")
    if not new_copy:
        recorded = _some_recorded_files()
        if recorded and not any(backend.exists(object_key(sha)) for sha in recorded):
            raise ValueError(
                f"store {FILE_STORE!r} at {location} holds none of the files this database "
                "records (not mounted? wrong location?); for a new copy, pass new_copy=True"
            )
    backend.put_buffer(_MARKER_CONTENT, STORE_MARKER)


def _some_recorded_files() -> list[str]:
    """SHA-256 of a few recorded files."""
    return [key["file_sha256"] for key in File.keys(limit=_SAMPLE)]
