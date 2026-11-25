"""``ingest``: one session folder in, everything registered and computed.

A cron job or a file watcher can call it.
"""

from __future__ import annotations

from pathlib import Path

from scene_pipelines.core import atomic
from scene_pipelines.schemas.scene.session import Session

from scene_onboarding_demo.layout import DATA
from scene_onboarding_demo.manifest import read_session_folder
from scene_onboarding_demo.register import (
    register_dlc_project,
    register_mouse,
    register_recording,
    register_session,
    register_session_details,
)
from scene_onboarding_demo.schemas import Kinematics, Trajectory

COMPUTED = (Trajectory, Kinematics)  # populate in this order


def ingest(folder: Path) -> dict:
    """Read and validate a session folder, register it, compute what is missing. Safe to rerun."""
    # 1. Read your data in Python
    manifest = read_session_folder(folder)

    # 2. Register your data in the database
    register_mouse(manifest.mouse)
    config = register_dlc_project(DATA / manifest.recording.dlc_project)
    with atomic(Session.connection):  # the session and its details: both, or neither
        session = register_session(manifest.session)
        register_session_details(manifest.session, session=session)
    register_recording(manifest.recording, session=session, config=config)

    # 3. Compute downstream analyses automatically
    for table in COMPUTED:
        table.populate()
    return session
