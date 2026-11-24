"""Unit tests for the dlc schema and helpers (no database)."""

import sys

import pytest
from scene_pipelines.core.access_markers import (
    SyncAuthority,
    WriteRole,
    sync_authority_of,
    write_role_of,
)
from scene_pipelines.ingestion.dlc import project as project_module
from scene_pipelines.ingestion.dlc._transient.config import ConfigRecord, read_project_config
from scene_pipelines.schemas.dlc.project import DlcProject, ProjectConfig

SINGLE = {
    "Task": "reach",
    "scorer": "someone",
    "date": "Jun26",
    "multianimalproject": False,
    "identity": None,
    "bodyparts": ["nose", "left_ear", "tail_base"],
    "multianimalbodyparts": [],
    "uniquebodyparts": [],
    "individuals": ["individual1"],
    "pcutoff": 0.6,
    "project_path": "/home/someone/reach-someone-2026-06-26",
}

MULTI = {
    **SINGLE,
    "multianimalproject": True,
    "identity": True,
    "bodyparts": "MULTI!",
    "multianimalbodyparts": ["nose", "tail_base"],
    "uniquebodyparts": ["port"],
    "individuals": ["mouse1", "mouse2"],
}


def write_config(path, config):
    """Write ``config`` as a config.yaml; returns its path."""
    from ruamel.yaml import YAML

    with path.open("w", encoding="utf-8") as file:
        YAML(typ="safe").dump(config, file)
    return path


def test_read_single_animal_config(tmp_path):
    path = write_config(tmp_path / "config.yaml", SINGLE)
    assert read_project_config(path) == ConfigRecord(
        task="reach",
        config_date="Jun26",
        multianimal=False,
        identity=False,
        pcutoff=0.6,
        bodyparts=("nose", "left_ear", "tail_base"),
        unique_bodyparts=(),
        individuals=(),
    )


def test_read_multi_animal_config(tmp_path):
    record = read_project_config(write_config(tmp_path / "config.yaml", MULTI))
    assert record.multianimal is True
    assert record.identity is True
    assert record.bodyparts == ("nose", "tail_base")
    assert record.unique_bodyparts == ("port",)
    assert record.individuals == ("mouse1", "mouse2")


def test_unset_identity_is_false(tmp_path):
    path = write_config(tmp_path / "config.yaml", {**MULTI, "identity": None})
    assert read_project_config(path).identity is False


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"bodyparts": []}, "no bodyparts"),
        ({"bodyparts": ["nose", "nose"]}, "more than once"),
        ({"bodyparts": ["x" * 65]}, "longer than 64"),
        ({"bodyparts": "nose"}, "list of names"),
        ({"pcutoff": None}, "pcutoff"),
        ({"Task": ""}, "Task is missing"),
        ({"date": None}, "date is missing"),
        ({"multianimalproject": "yes"}, "multianimalproject"),
    ],
)
def test_read_config_refuses_malformed_fields(tmp_path, change, message):
    path = write_config(tmp_path / "config.yaml", {**SINGLE, **change})
    with pytest.raises(ValueError, match=message):
        read_project_config(path)


def test_read_config_refuses_a_file_that_is_no_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a mapping"):
        read_project_config(path)


def test_read_config_refuses_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        read_project_config(tmp_path / "config.yaml")


def test_read_config_names_the_extra_without_ruamel(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("Task: reach\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "ruamel.yaml", None)  # makes the import raise ImportError
    with pytest.raises(ImportError, match=r"scene-pipelines\[dlc\]"):
        read_project_config(path)


def test_register_project_config_writes_nothing_for_an_unreadable_config(tmp_path, monkeypatch):
    def refuse(path):
        raise ValueError("unreadable")

    def must_not_register(path, *, store):
        raise AssertionError("File was written for an unreadable config")

    monkeypatch.setattr(project_module, "read_project_config", refuse)
    monkeypatch.setattr(project_module, "register_file", must_not_register)
    with pytest.raises(ValueError, match="unreadable"):
        project_module.register_project_config(
            tmp_path / "config.yaml", dlc_project={"lab_id": "lab", "dlc_project_id": "id"}
        )


def test_register_dlc_project_refuses_an_invalid_code():
    with pytest.raises(ValueError, match="dlc_project_code"):
        project_module.register_dlc_project("my project", lab={"lab_id": "lab"})


def test_keypoint_parts_keep_config_order(tmp_path):
    record = read_project_config(write_config(tmp_path / "config.yaml", MULTI))
    parts = project_module._keypoint_parts(record)
    assert parts[ProjectConfig.Bodypart] == [
        {"bodypart_index": 0, "bodypart": "nose"},
        {"bodypart_index": 1, "bodypart": "tail_base"},
    ]
    assert parts[ProjectConfig.UniqueBodypart] == [
        {"unique_bodypart_index": 0, "unique_bodypart": "port"}
    ]
    assert parts[ProjectConfig.Individual] == [
        {"individual_index": 0, "individual": "mouse1"},
        {"individual_index": 1, "individual": "mouse2"},
    ]


@pytest.mark.parametrize(
    "table",
    [DlcProject, ProjectConfig, ProjectConfig.Bodypart, ProjectConfig.Individual],
)
def test_dlc_tables_are_acquired_origin_data(table):
    assert sync_authority_of(table) is SyncAuthority.ORIGIN
    assert write_role_of(table) is WriteRole.ACQUISITION
