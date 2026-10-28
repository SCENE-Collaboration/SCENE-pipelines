"""Shared DataJoint schema object and DDL version for the file catalogue."""

from scene_pipelines.core import SCENE_REGISTRY
from scene_pipelines.core.versioning import SchemaVersionTable

schema = SCENE_REGISTRY.make_schema("files")

FILES_SCHEMA_VERSION = "0.0.1"


@schema
class SchemaVersion(SchemaVersionTable):
    """Definition versions applied to this files database (see ``SchemaVersionTable``)."""

    code_version = FILES_SCHEMA_VERSION
