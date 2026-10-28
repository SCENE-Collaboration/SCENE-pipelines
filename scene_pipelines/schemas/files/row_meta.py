"""Row-level write provenance for the file catalogue.

Lives in the files schema, not in ``provenance``, so labs without files never
have to activate it. ``File`` is not stamped: its rows are facts about bytes.
"""

from scene_pipelines.schemas.files._schema import schema
from scene_pipelines.schemas.files.files import Location, Store
from scene_pipelines.schemas.provenance.deployment import Deployment  # noqa: F401
from scene_pipelines.schemas.provenance.row_meta import RowMetaBase


@schema
class StoreRowMeta(RowMetaBase):
    """Provenance for one ``Store`` row."""

    tracked_table = Store
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class LocationRowMeta(RowMetaBase):
    """Provenance for one ``Location`` row: who recorded the copy, and when."""

    tracked_table = Location
    definition = RowMetaBase.build_definition(tracked_table)
