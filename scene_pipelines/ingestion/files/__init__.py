"""Write helpers for the file catalogue (Store, File, Location).

Importing this package registers the files schema, so it is not re-exported
from ``scene_pipelines.ingestion``: labs without files never import it.
``Store`` is an admin catalog: see ``scene_pipelines.ingestion.files.admin``.
"""

from scene_pipelines.ingestion.files._version import FILES_WRITER_VERSION
from scene_pipelines.ingestion.files.files import (
    hash_file,
    locations,
    object_key,
    record_stored,
    register_file,
    remove_location,
)

__all__ = [
    "FILES_WRITER_VERSION",
    "hash_file",
    "locations",
    "object_key",
    "record_stored",
    "register_file",
    "remove_location",
]
