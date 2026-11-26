"""The lab's codes: set once by an admin, used by every session."""

LAB = {"lab_id": "demo", "lab_name": "DEMO lab", "institution": "SCENE workshop"}
PROJECT = {
    "project_name": "demo_active_sensing",
    "project_title": "DEMO: active sensing in a 52 cm open field",
}

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

LAB_KEY = {"lab_id": LAB["lab_id"]}
PROJECT_KEY = {"project_name": PROJECT["project_name"]}
