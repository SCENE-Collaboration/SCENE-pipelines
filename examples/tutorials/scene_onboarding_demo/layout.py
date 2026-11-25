"""The Demo lab's layout: how its data is organised on disk.

    scene_onboarding_data/                       next to the notebook: the unpacked data zip
    ├── sessions/
    │   ├── mice.json                            the lab's mice: name, sex, birth date, strain
    │   └── <mouse>_<YYYY-MM-DD>_<attempt>/      one folder per session, named by its code
    │       ├── <mouse>_<YYYY-MM-DD>_<attempt>.json  the transfer GUI's file: details + welfare
    │       └── recording.json                   the tracked video: camera, video, poses, arena
    ├── active_sensing_ephys-celia-2026-06-26/   the DeepLabCut project, offline video and poses
    └── live/                                    the live recordings, poses and frame times

recording.json names its files relative to that folder.
"""

from __future__ import annotations

import re
from pathlib import Path

# Where the lab's data lives: the one line to change to use another copy.
DATA = Path(__file__).resolve().parents[1] / "scene_onboarding_data"
SESSIONS = DATA / "sessions"
MICE_FILE = SESSIONS / "mice.json"
RECORDING_FILE = "recording.json"
SESSION_FOLDER = re.compile(r".+_\d{4}-\d{2}-\d{2}_\d+")  # <mouse>_<YYYY-MM-DD>_<attempt>

# Who writes: registered once (``setup_lab``), referred to by every session.
LAB = {"lab_id": "demo", "lab_name": "DEMO lab", "institution": "SCENE workshop"}
PROJECT = {
    "project_name": "demo_active_sensing",
    "project_title": "DEMO: active sensing in a 52 cm open field",
}
CAMERAS = {"top": "overhead camera of the open field"}

# The GUI records the experimenter's name; only a pseudonymous code is shared.
EXPERIMENTER_CODES = {
    "John Demo": "E01",
    "Jane Doe": "E02",
    "Jill Doe": "E03",
}

# DeepLabCut names a project folder after its task, labeller and date; the shared code must
# not name a person.
DLC_PROJECT_CODES = {
    "active_sensing_ephys-celia-2026-06-26": "active-sensing-ephys",
}


def discover_sessions() -> list[Path]:
    """Every session folder under ``sessions/``, sorted by name: per mouse, then by date."""
    return sorted(
        path for path in SESSIONS.iterdir() if path.is_dir() and SESSION_FOLDER.fullmatch(path.name)
    )


def gui_file(session_folder: Path) -> Path:
    """The transfer GUI's file of a session folder: named like the folder."""
    return session_folder / f"{session_folder.name}.json"
