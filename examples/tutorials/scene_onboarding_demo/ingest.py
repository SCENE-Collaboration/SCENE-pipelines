"""Ingest the lab's session folders: by hand, from cron, or after a transfer.

    python -m scene_onboarding_demo.ingest <data>/sessions

Run it from ``examples/tutorials/``. DataJoint takes the connection from ``DJ_HOST``, ``DJ_USER``
and ``DJ_PASS``; SCENE takes the schema prefix from ``DJ_SCHEMA_PREFIX`` and the deployment from
``SCENE_DEPLOYMENT_ID``. Folders already in the database are skipped; a folder that fails is
logged, and the exit code is 1.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from scene_pipelines.core import SCENE_REGISTRY, atomic
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
    discover_sessions,
    read_session_folder,
    read_video_timestamps,
)
from scene_onboarding_demo.register import register_recording, register_session_details
from scene_onboarding_demo.schemas import Kinematics, Recording, Trajectory

log = logging.getLogger(__name__)


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


def is_ingested(folder: Path) -> bool:
    """Whether the session of a folder has its ``Recording`` in the database."""
    return bool(Recording * Session & {**LAB_KEY, "session_code": Path(folder).name})


def ingest_all(sessions: Path) -> list[Path]:
    """Ingest every session folder not yet in the database.

    Returns:
        The folders that failed.
    """
    failed = []
    for folder in discover_sessions(sessions):
        if is_ingested(folder):
            continue
        try:
            ingest(folder)
            log.info("ingested %s", folder.name)
        except Exception:
            log.exception("failed: %s", folder.name)
            failed.append(folder)
    return failed


def main() -> None:
    """Ingest the session folders given on the command line; exit code 1 if any failed."""
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scene_onboarding_demo.ingest <data>/sessions")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    SCENE_REGISTRY.activate_all()
    sys.exit(1 if ingest_all(Path(sys.argv[1])) else 0)


if __name__ == "__main__":
    main()
