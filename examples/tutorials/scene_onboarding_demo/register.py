"""Write the lab's own tables of a session, on top of the shared rows.

``ingest`` (in ``scene_onboarding_demo.ingest``) calls these after the shared helpers of
``scene_pipelines.ingestion``. Both can run again: what is stored already is not written twice.
"""

from __future__ import annotations

import numpy as np

from scene_onboarding_demo.manifest import RecordingEntry, SessionEntry
from scene_onboarding_demo.schemas import Arena, Recording, ScoreSheet, SessionInfo


def register_session_details(entry: SessionEntry, *, session: dict) -> None:
    """The lab's ``SessionInfo`` and ``ScoreSheet`` of a session."""
    info = {"attempt", "rig_id", "task_name", "anesthesia_name", "opto_name", "session_notes"}
    welfare = {"license", "body_condition", "general_assay", "housing_assay", "weight_percentage"}
    SessionInfo.insert1({**session, **entry.model_dump(include=info)}, skip_duplicates=True)
    ScoreSheet.insert1({**session, **entry.model_dump(include=welfare)}, skip_duplicates=True)


def register_recording(entry: RecordingEntry, *, video: dict, pose: dict, config: dict) -> dict:
    """The lab's ``Recording``: a shared video and its poses, with the lab's arena.

    Returns:
        The ``Recording`` key: the video's.
    """
    Arena.insert1(entry.arena.model_dump(exclude={"corners_px"}), skip_duplicates=True)
    Recording.insert1(
        {
            **video,
            **pose,
            "dlc_project_id": config["dlc_project_id"],
            "config_sha256": config["file_sha256"],
            "arena_name": entry.arena.arena_name,
            "corners_px": np.array(entry.arena.corners_px),
            "video_path": entry.video.as_posix(),
        },
        skip_duplicates=True,
    )
    return video
