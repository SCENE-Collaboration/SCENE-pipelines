"""Write the lab's records, in two layers, and ``ingest``: one session folder in, all written.

Shared layer, through scene-pipelines: ``register_mouse``, ``register_session``,
``register_dlc_project``. Lab layer, the lab's own tables: ``register_session_details``,
``register_recording`` (which also registers the shared video and poses it refers to).

Every function can run again: what is stored already is recognised, not written twice.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scene_pipelines.core import atomic
from scene_pipelines.ingestion import register_session as register_shared_session
from scene_pipelines.ingestion import subject_key
from scene_pipelines.ingestion.dlc import register_dlc_project as register_shared_dlc_project
from scene_pipelines.ingestion.dlc import register_pose, register_project_config
from scene_pipelines.ingestion.mouse import ensure_strain
from scene_pipelines.ingestion.mouse import register_mouse as register_shared_mouse
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
    MouseEntry,
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

COMPUTED = (Trajectory, Kinematics)  # populate in this order


def register_mouse(mouse: MouseEntry) -> dict:
    """A mouse, as a shared ``Subject`` with its ``Mouse`` row and strain."""
    strain = ensure_strain({"strain_name": mouse.strain})
    return register_shared_mouse(
        mouse.mouse_name,
        mouse.sex,
        lab=LAB_KEY,
        date_of_birth=mouse.date_of_birth,
        strain=strain,
        genotype=mouse.genotype or None,
    )


def register_session(entry: SessionEntry) -> dict:
    """Shared layer: the ``Session`` with its mouse, project and experimenter."""
    return register_shared_session(
        entry.session_code,
        entry.session_date,
        lab=LAB_KEY,
        subjects=[subject_key(entry.mouse_name, lab=LAB_KEY)],
        project=PROJECT_KEY,
        experimenter={**LAB_KEY, "experimenter_code": EXPERIMENTER_CODES[entry.experimenter_name]},
    )


def register_session_details(entry: SessionEntry, *, session: dict) -> None:
    """Lab layer: what this lab records about a session, ``SessionInfo`` and ``ScoreSheet``."""
    info = {"attempt", "rig_id", "task_name", "anesthesia_name", "opto_name", "session_notes"}
    welfare = {"license", "body_condition", "general_assay", "housing_assay", "weight_percentage"}
    SessionInfo.insert1({**session, **entry.model_dump(include=info)}, skip_duplicates=True)
    ScoreSheet.insert1({**session, **entry.model_dump(include=welfare)}, skip_duplicates=True)


def register_dlc_project(folder: Path) -> dict:
    """Shared layer: a DeepLabCut project, by its lab code, and its ``config.yaml``.

    Returns:
        The ``ProjectConfig`` key: the project and the config version.
    """
    folder = Path(folder)
    if folder.name not in DLC_PROJECT_CODES:
        raise ValueError(f"no lab code for the DeepLabCut project {folder.name!r}")
    project = register_shared_dlc_project(
        DLC_PROJECT_CODES[folder.name], lab=LAB_KEY, scene_project=PROJECT_KEY
    )
    return register_project_config(folder / "config.yaml", dlc_project=project)


def register_recording(entry: RecordingEntry, *, session: dict, config: dict) -> dict:
    """A tracked video of a session: the shared video and poses, then the lab's ``Recording``."""
    start_time, timestamps = None, None
    if entry.video_timestamps is not None:
        start_time, timestamps = read_video_timestamps(entry.data / entry.video_timestamps)

    with atomic(Recording.connection):  # the video, its poses and the recording: all or none
        video = register_video_recording(
            entry.data / entry.video,
            session=session,
            take=entry.take,
            frame_timestamps=timestamps,
            start_time=start_time,
        )
        pose = register_pose(
            entry.data / entry.poses,
            dlc_project={k: config[k] for k in ("lab_id", "dlc_project_id")},
            video={"file_sha256": (VideoRecording & video).fetch1("file_sha256")},
            frame_times=entry.data / entry.frame_times if entry.frame_times else None,
        )
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

    # 2. Register your data in the database
    config = register_dlc_project(manifest.recording.data / manifest.recording.dlc_project)
    register_mouse(manifest.mouse)
    with atomic(Session.connection):  # the session and its details: both, or neither
        session = register_session(manifest.session)
        register_session_details(manifest.session, session=session)
    register_recording(manifest.recording, session=session, config=config)

    # 3. Compute downstream analyses automatically
    for table in COMPUTED:
        table.populate()
    return session
