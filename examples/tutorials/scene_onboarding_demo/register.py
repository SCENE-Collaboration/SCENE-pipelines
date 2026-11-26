"""Write the lab's own tables, and ``ingest``: one session folder in, all written.

The shared tables are written by the helpers of ``scene_pipelines.ingestion``; the two functions
here add the lab's rows on top. Every function can run again: what is stored already is
recognised, not written twice.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scene_pipelines.core import atomic
from scene_pipelines.ingestion import register_session
from scene_pipelines.ingestion.dlc import (
    register_dlc_project,
    register_pose,
    register_project_config,
)
from scene_pipelines.ingestion.mouse import ensure_strain, register_mouse
from scene_pipelines.ingestion.video import register_video_recording
from scene_pipelines.schemas.scene.session import Session
from scene_pipelines.schemas.video.recording import VideoRecording

from scene_onboarding_demo.admin import (
    DLC_PROJECT_CODES,
    EXPERIMENTER_CODES,
    LAB_KEY,
    PROJECT_KEY,
)
from scene_onboarding_demo.manifest import (
    RecordingEntry,
    SessionEntry,
    read_session_folder,
    read_video_timestamps,
)
from scene_onboarding_demo.schemas import (
    Arena,
    Kinematics,
    Recording,
    ScoreSheet,
    SessionInfo,
    Trajectory,
)


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


def ingest(folder: Path) -> dict:
    """Read and validate a session folder, register it, compute what is missing. Safe to rerun."""
    # 1. Read your data in Python
    manifest = read_session_folder(folder)
    mouse, details, rec = manifest.mouse, manifest.session, manifest.recording

    # 2a. The shared layer: the DeepLabCut project, the mouse and the session
    project = register_dlc_project(
        DLC_PROJECT_CODES[rec.dlc_project.name], lab=LAB_KEY, scene_project=PROJECT_KEY
    )
    config = register_project_config(
        rec.data / rec.dlc_project / "config.yaml", dlc_project=project
    )
    subject = register_mouse(
        mouse.mouse_name,
        mouse.sex,
        lab=LAB_KEY,
        date_of_birth=mouse.date_of_birth,
        strain=ensure_strain({"strain_name": mouse.strain}),
        genotype=mouse.genotype or None,
    )
    with atomic(Session.connection):  # the session and its details: both, or neither
        session = register_session(
            details.session_code,
            details.session_date,
            lab=LAB_KEY,
            subjects=[subject],
            project=PROJECT_KEY,
            experimenter={
                **LAB_KEY,
                "experimenter_code": EXPERIMENTER_CODES[details.experimenter_name],
            },
        )
        # 2b. The lab layer on top
        register_session_details(details, session=session)

    # 2c. The recording: shared video and poses, then the lab's Recording
    start_time, timestamps = None, None
    if rec.video_timestamps is not None:
        start_time, timestamps = read_video_timestamps(rec.data / rec.video_timestamps)
    with atomic(Recording.connection):  # the video, its poses and the recording: all or none
        video = register_video_recording(
            rec.data / rec.video,
            session=session,
            take=rec.take,
            frame_timestamps=timestamps,
            start_time=start_time,
        )
        pose = register_pose(
            rec.data / rec.poses,
            dlc_project=project,
            video={"file_sha256": (VideoRecording & video).fetch1("file_sha256")},
            frame_times=rec.data / rec.frame_times if rec.frame_times else None,
        )
        register_recording(rec, video=video, pose=pose, config=config)

    # 3. Compute downstream analyses automatically
    Trajectory.populate()
    Kinematics.populate()
    return session
