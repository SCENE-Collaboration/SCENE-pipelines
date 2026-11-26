"""The lab's files, read into validated objects before anything touches the database.

The data folder holds ``sessions/``: ``mice.json`` and one folder per session, named by its code
(``<mouse>_<YYYY-MM-DD>_<attempt>``), with the transfer GUI's file (named like the folder) and
``recording.json``, whose paths are relative to the data folder.

A wrong or missing field fails here, by name. ``read_session_folder`` collects one session folder
into a ``SessionManifest``: everything ``ingest`` needs (the mouse, the session, the recording),
with the paths checked.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

MICE_FILE = "mice.json"
RECORDING_FILE = "recording.json"
SESSION_FOLDER = re.compile(r".+_\d{4}-\d{2}-\d{2}_\d+")  # <mouse>_<YYYY-MM-DD>_<attempt>


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
    """``recording.json``: the tracked video of a session. Paths are relative to ``data``."""

    data: Path  # the data folder; set by read_session_folder, not in recording.json
    session_code: str
    camera: str  # the lab's camera name; kept in the lab's files, not shared
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
            if path is not None and not (self.data / path).exists():
                raise ValueError(f"missing: {path}")
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


def discover_sessions(sessions: Path) -> list[Path]:
    """Every session folder in ``sessions``, sorted by name: per mouse, then by date."""
    return sorted(
        path
        for path in Path(sessions).iterdir()
        if path.is_dir() and SESSION_FOLDER.fullmatch(path.name)
    )


def gui_file(session_folder: Path) -> Path:
    """The transfer GUI's file of a session folder: named like the folder."""
    return session_folder / f"{session_folder.name}.json"


def read_mice(path: Path) -> list[MouseEntry]:
    return [MouseEntry(**mouse) for mouse in read_json(path)]


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
    data = folder.parent.parent  # <data>/sessions/<session>
    session = SessionEntry(**read_json(gui_file(folder)))
    mice = {mouse.mouse_name: mouse for mouse in read_mice(folder.parent / MICE_FILE)}
    if session.mouse_name not in mice:
        raise ValueError(f"{session.mouse_name!r} is not in {MICE_FILE}")
    return SessionManifest(
        folder=folder,
        mouse=mice[session.mouse_name],
        session=session,
        recording=RecordingEntry(**read_json(folder / RECORDING_FILE), data=data),
    )
