"""The Demo lab's own details of a session: what the shared ``Session`` does not hold.

Both tables hang off the shared ``Session``, one row per session, filled from the transfer GUI's
file.
"""

import datajoint as dj
from scene_pipelines.core import SCENE_REGISTRY
from scene_pipelines.schemas.scene.session import Session  # noqa: F401  # FK: -> Session

schema = SCENE_REGISTRY.make_schema("lab")


@schema
class SessionInfo(dj.Manual):
    definition = """
    # how the session was run
    -> Session
    ---
    attempt: int32                 # counter for sessions of one mouse on one day
    rig_id: int32
    task_name: varchar(100)
    anesthesia_name: varchar(20)
    opto_name: varchar(128)
    session_notes='': varchar(4095)
    """


@schema
class ScoreSheet(dj.Manual):
    definition = """
    # welfare check of the session's mouse
    -> Session
    ---
    license: varchar(128)
    body_condition: varchar(32)
    general_assay: varchar(32)
    housing_assay: varchar(8)
    weight_percentage: float32     # weight change from baseline, in percent
    """
