"""Write the lab's records, in two layers.

Shared layer, through scene-pipelines: ``setup_lab``, ``register_mouse``, ``register_session``,
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
from scene_pipelines.ingestion.provenance import DuplicatePolicy
from scene_pipelines.ingestion.scene.admin import ensure_lab, ensure_project
from scene_pipelines.ingestion.video import ensure_camera, register_video_recording
from scene_pipelines.schemas.scene.session import Experimenter
from scene_pipelines.schemas.video.recording import VideoRecording

from scene_onboarding_demo.layout import (
    CAMERAS,
    DATA,
    DLC_PROJECT_CODES,
    EXPERIMENTER_CODES,
    LAB,
    PROJECT,
)
from scene_onboarding_demo.manifest import (
    MouseEntry,
    RecordingEntry,
    SessionEntry,
    read_video_timestamps,
)
from scene_onboarding_demo.schemas import Arena, Recording, ScoreSheet, SessionInfo

LAB_KEY = {"lab_id": LAB["lab_id"]}
PROJECT_KEY = {"project_name": PROJECT["project_name"]}


def setup_lab() -> None:
    """Once per lab: the lab, its project, its experimenters' codes and its cameras."""
    ensure_lab(LAB, if_exists=DuplicatePolicy.VERIFY)
    ensure_project(PROJECT, if_exists=DuplicatePolicy.VERIFY)
    for code in EXPERIMENTER_CODES.values():
        Experimenter.insert1({**LAB_KEY, "experimenter_code": code}, skip_duplicates=True)
    for code, details in CAMERAS.items():
        ensure_camera(code, lab=LAB_KEY, camera_details=details)


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
    project = register_shared_dlc_project(
        DLC_PROJECT_CODES[Path(folder).name], lab=LAB_KEY, scene_project=PROJECT_KEY
    )
    return register_project_config(Path(folder) / "config.yaml", dlc_project=project)


def register_recording(entry: RecordingEntry, *, session: dict, config: dict) -> dict:
    """A tracked video of a session: the shared video and poses, then the lab's ``Recording``."""
    start_time, timestamps = None, None
    if entry.video_timestamps is not None:
        start_time, timestamps = read_video_timestamps(DATA / entry.video_timestamps)

    with atomic(Recording.connection):  # the video, its poses and the recording: all or none
        video = register_video_recording(
            DATA / entry.video,
            session=session,
            camera={**LAB_KEY, "camera_code": entry.camera},
            take=entry.take,
            frame_timestamps=timestamps,
            start_time=start_time,
        )
        pose = register_pose(
            DATA / entry.poses,
            dlc_project={k: config[k] for k in ("lab_id", "dlc_project_id")},
            video={"file_sha256": (VideoRecording & video).fetch1("file_sha256")},
            frame_times=DATA / entry.frame_times if entry.frame_times else None,
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
