"""The lab's files, read into validated objects before anything touches the database.

A wrong or missing field fails here, by name. ``read_session_folder`` collects one session folder
into a ``SessionManifest``: everything ``ingest`` needs (the mouse, the session, the recording),
with the paths checked.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from scene_onboarding_demo.layout import (
    DATA,
    DLC_PROJECT_CODES,
    MICE_FILE,
    RECORDING_FILE,
    gui_file,
)


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # unknown fields are errors


class MouseEntry(Entry):
    """One mouse of ``mice.json``."""

    mouse_name: str
    sex: Literal["M", "F", "U"]
    date_of_birth: date
    strain: str  # official nomenclature, e.g. C57BL/6J
    genotype: str = ""


class SessionEntry(Entry):
    """The transfer GUI's file of one session (the MouseAR format)."""

    mouse_name: str
    session_date: date = Field(alias="doe")  # the GUI calls it 'doe', date of experiment
    attempt: int = Field(ge=1)
    experimenter_name: str
    rig_id: int
    task_name: str
    anesthesia_name: str = "awake"
    opto_name: str = "none"
    session_notes: str = ""
    # the welfare check, done at the session
    license: str
    body_condition: str
    general_assay: str
    housing_assay: str
    weight_percentage: float

    @property
    def session_code(self) -> str:
        return f"{self.mouse_name}_{self.session_date}_{self.attempt}"


class ArenaEntry(Entry):
    arena_name: str
    width_cm: float
    depth_cm: float
    # floor corners in the image, clockwise from top-left
    corners_px: list[tuple[float, float]] = Field(min_length=4, max_length=4)


class RecordingEntry(Entry):
    """``recording.json``: the tracked video of a session. Paths are relative to ``layout.DATA``."""

    session_code: str
    camera: str  # the lab's camera code
    take: int = Field(default=1, ge=1)
    dlc_project: Path  # the DeepLabCut project folder
    video: Path
    video_timestamps: Path | None = None  # the recorder's frame times (.json), if any
    poses: Path  # DeepLabCut output .h5
    frame_times: Path | None  # DLC-live's time of each pose (.csv), if any
    arena: ArenaEntry

    @model_validator(mode="after")
    def _files_exist(self):
        paths = (self.dlc_project, self.video, self.video_timestamps, self.poses, self.frame_times)
        for path in paths:
            if path is not None and not (DATA / path).exists():
                raise ValueError(f"missing: {path}")
        if self.dlc_project.name not in DLC_PROJECT_CODES:
            raise ValueError(f"no lab code for the DeepLabCut project {self.dlc_project.name!r}")
        return self


class SessionManifest(Entry):
    """Everything in one session folder, validated and consistent."""

    folder: Path
    mouse: MouseEntry
    session: SessionEntry
    recording: RecordingEntry

    @model_validator(mode="after")
    def _same_session(self):
        codes = {self.folder.name, self.session.session_code, self.recording.session_code}
        if len(codes) > 1:
            raise ValueError(
                "the folder name, the GUI file and recording.json name different sessions: "
                f"{sorted(codes)}"
            )
        if self.mouse.mouse_name != self.session.mouse_name:
            raise ValueError(
                f"the session is of {self.session.mouse_name!r}, not {self.mouse.mouse_name!r}"
            )
        return self


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_mice() -> list[MouseEntry]:
    return [MouseEntry(**mouse) for mouse in read_json(MICE_FILE)]


def as_dataframe(mice: list[MouseEntry]) -> pd.DataFrame:
    return pd.DataFrame([mouse.model_dump() for mouse in mice])


def read_video_timestamps(path: Path) -> tuple[datetime, np.ndarray]:
    """The recorder's start time (UTC) and the time of each frame, in epoch seconds."""
    record = read_json(path)
    times = np.array([frame["software_timestamp"] for frame in record["frame_timestamps"]])
    start = datetime.fromtimestamp(record["start_time"], tz=timezone.utc).replace(tzinfo=None)
    return start, times


def read_session_folder(folder: Path) -> SessionManifest:
    """One session folder, with its mouse from ``mice.json``; an unknown mouse fails here."""
    folder = Path(folder)
    session = SessionEntry(**read_json(gui_file(folder)))
    mice = {mouse.mouse_name: mouse for mouse in read_mice()}
    if session.mouse_name not in mice:
        raise ValueError(f"{session.mouse_name!r} is not in {MICE_FILE.name}")
    return SessionManifest(
        folder=folder,
        mouse=mice[session.mouse_name],
        session=session,
        recording=RecordingEntry(**read_json(folder / RECORDING_FILE)),
    )
