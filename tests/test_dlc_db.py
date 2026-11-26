"""Live-DB tests for the dlc helpers."""

import os

import pytest

pytest.importorskip("ruamel.yaml")

from test_dlc import MULTI, SINGLE, write_config  # noqa: E402

_TRUTHY = frozenset({"1", "true", "yes", "on"})

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.getenv("DJ_HOST"),
        reason="requires DataJoint DB (set DJ_HOST)",
    ),
    pytest.mark.skipif(
        (os.getenv("AUTO_ACTIVATE") or "").strip().lower() not in _TRUTHY,
        reason="tables are unbound unless AUTO_ACTIVATE is set",
    ),
]


@pytest.fixture
def lab(dj_connection, monkeypatch):
    """A registered lab; also sets the deployment that stamps the rows."""
    from scene_pipelines.ingestion.provenance import DuplicatePolicy
    from scene_pipelines.ingestion.scene.admin import ensure_lab

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    return ensure_lab({"lab_id": "dlc_lab", "lab_name": "DLC Lab"}, if_exists=DuplicatePolicy.SKIP)


def test_register_dlc_project_mints_an_id_once(lab):
    from scene_pipelines.ingestion.dlc import dlc_project_key, register_dlc_project
    from scene_pipelines.ingestion.provenance import DuplicatePolicy
    from scene_pipelines.ingestion.scene.admin import ensure_project
    from scene_pipelines.schemas.dlc.project import DlcProject
    from scene_pipelines.schemas.dlc.row_meta import DlcProjectRowMeta

    project = register_dlc_project("reach-2026", lab=lab)

    assert set(project) == {"lab_id", "dlc_project_id"}
    assert register_dlc_project("reach-2026", lab=lab) == project
    assert dlc_project_key("reach-2026", lab=lab) == project
    assert (DlcProject & project).fetch1("dlc_project_code") == "reach-2026"
    assert (DlcProjectRowMeta & project).fetch1("origin_deployment_id") == "test-local"
    assert register_dlc_project("reach-other", lab=lab) != project

    scene_project = ensure_project({"project_name": "dlc_test"}, if_exists=DuplicatePolicy.SKIP)
    with pytest.raises(ValueError, match="different content hash"):
        register_dlc_project("reach-2026", lab=lab, scene_project=scene_project)
    linked = register_dlc_project(
        "reach-2026", lab=lab, scene_project=scene_project, if_exists=DuplicatePolicy.OVERWRITE
    )
    assert linked == project
    assert (DlcProject & project).fetch1("project_name") == "dlc_test"


def test_dlc_project_key_refuses_an_unknown_code(lab):
    from scene_pipelines.ingestion.dlc import dlc_project_key

    with pytest.raises(ValueError, match="no DeepLabCut project"):
        dlc_project_key("never-registered", lab=lab)


def test_register_project_config_once_per_file(lab, tmp_path):
    from scene_pipelines.ingestion.dlc import register_dlc_project, register_project_config
    from scene_pipelines.ingestion.files import hash_file
    from scene_pipelines.schemas.dlc.project import ProjectConfig
    from scene_pipelines.schemas.files.files import FileContent

    project = register_dlc_project("single-config", lab=lab)
    path = write_config(tmp_path / "config.yaml", SINGLE)
    config = register_project_config(path, dlc_project=project)

    assert config == {**project, "file_sha256": hash_file(path).sha256}
    assert register_project_config(path, dlc_project=project) == config
    row = (ProjectConfig & config).fetch1()
    assert (row["task"], row["config_date"], row["multianimal"], row["identity"]) == (
        "reach",
        "Jun26",
        False,
        False,
    )
    assert row["pcutoff"] == pytest.approx(0.6)
    bodyparts = (ProjectConfig.Bodypart & config).to_dicts(order_by="bodypart_index")
    assert [b["bodypart"] for b in bodyparts] == ["nose", "left_ear", "tail_base"]
    assert not (ProjectConfig.Individual & config)
    assert not (FileContent & config)  # store=False by default

    edited = write_config(tmp_path / "edited.yaml", {**SINGLE, "pcutoff": 0.9})
    assert register_project_config(edited, dlc_project=project) != config
    assert len(ProjectConfig & project) == 2


def test_register_multi_animal_project_config(lab, tmp_path):
    from scene_pipelines.ingestion.dlc import register_dlc_project, register_project_config
    from scene_pipelines.schemas.dlc.project import ProjectConfig

    project = register_dlc_project("multi-config", lab=lab)
    config = register_project_config(
        write_config(tmp_path / "config.yaml", MULTI), dlc_project=project
    )

    assert (ProjectConfig & config).fetch1("multianimal", "identity") == (True, True)
    unique = (ProjectConfig.UniqueBodypart & config).fetch("unique_bodypart")
    individuals = (ProjectConfig.Individual & config).to_dicts(order_by="individual_index")
    assert list(unique) == ["port"]
    assert [i["individual"] for i in individuals] == ["mouse1", "mouse2"]
