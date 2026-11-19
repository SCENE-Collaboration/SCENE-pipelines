"""Write helpers for ``File``: put the bytes in the ``scene-files`` store, then record them.

Importing this package registers the files schema, so it is not re-exported
from ``scene_pipelines.ingestion``: labs without files never import it.
See ``scene_pipelines.ingestion.files.files`` for how to configure the store.
"""

from scene_pipelines.ingestion.files.files import (
    hash_file,
    record_file,
    register_file,
)
from scene_pipelines.schemas.files.files import FILE_STORE, object_key

__all__ = [
    "FILE_STORE",
    "hash_file",
    "object_key",
    "record_file",
    "register_file",
]
