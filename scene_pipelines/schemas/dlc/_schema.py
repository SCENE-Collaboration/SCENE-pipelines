"""Shared DataJoint schema object and DDL version for DeepLabCut tables."""

from scene_pipelines.core import SCENE_REGISTRY
from scene_pipelines.core.versioning import SchemaVersionTable

schema = SCENE_REGISTRY.make_schema("dlc")

DLC_SCHEMA_VERSION = "0.0.1"


@schema
class SchemaVersion(SchemaVersionTable):
    """Definition versions applied to this dlc database (see ``SchemaVersionTable``)."""

    code_version = DLC_SCHEMA_VERSION
