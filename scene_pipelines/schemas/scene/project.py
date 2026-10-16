"""SCENE-shared project catalog."""

import datajoint as dj

from scene_pipelines.core.access_markers import (
    SyncAuthority,
    WriteRole,
    mark_sync_authority,
    mark_write_role,
)
from scene_pipelines.schemas.scene._schema import schema


@mark_sync_authority(SyncAuthority.CENTRAL)
@mark_write_role(WriteRole.ADMIN)
@schema
class Project(dj.Manual):
    """Admin-only insertion: shared project catalog."""

    definition = """
    project_name: varchar(100)  # stable id, e.g. mousear
    ---
    project_title='': varchar(255)  # human-readable label
    """
