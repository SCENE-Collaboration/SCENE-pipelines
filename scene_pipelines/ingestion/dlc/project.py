"""Register DeepLabCut projects (DlcProject) and their config.yaml files (ProjectConfig)."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from scene_pipelines.core.config import deployment_row_from_settings, lab_key_from_settings
from scene_pipelines.core.db import atomic, lookup_key, new_id
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.dlc._transient.config import ConfigRecord, read_project_config
from scene_pipelines.ingestion.dlc._version import DLC_WRITER_VERSION
from scene_pipelines.ingestion.files import register_file
from scene_pipelines.ingestion.normalization.code import normalize_code
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.schemas.dlc.project import DlcProject, ProjectConfig
from scene_pipelines.schemas.dlc.row_meta import DlcProjectRowMeta, ProjectConfigRowMeta
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.scene.lab import Lab
from scene_pipelines.schemas.scene.project import Project


def register_dlc_project(
    dlc_project_code: str,
    *,
    lab: DjKey[Lab],
    scene_project: DjKey[Project] | None = None,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[DlcProject]:
    """Register a DeepLabCut project by its lab code; mint ``dlc_project_id`` when new.

    Args:
        dlc_project_code: Code unique within ``lab``; see ``normalize_code``.
        lab: Existing lab primary key, e.g. ``{"lab_id": "mlai"}``.
        scene_project: Optional existing SCENE ``Project`` key.
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when ``dlc_project_code`` is already registered in ``lab``; see
            ``DuplicatePolicy``.

    Returns:
        ``DlcProject`` primary key ``{lab_id: ..., dlc_project_id: ...}``.

    Raises:
        ValueError: If ``dlc_project_code`` is not a valid code, ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects the existing row.
    """
    code = normalize_code(dlc_project_code, field="dlc_project_code", max_length=128)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()

    with atomic(DlcProject.connection):
        existing = lookup_key(DlcProject, {**lab, "dlc_project_code": code})
        row = {
            **lab,
            "dlc_project_id": existing["dlc_project_id"] if existing else new_id(),
            "dlc_project_code": code,
            **(scene_project or {}),
        }
        return insert_tracked_row(
            DlcProjectRowMeta,
            row,
            payload={
                "dlc_project_code": code,
                "project_name": (scene_project or {}).get("project_name"),
            },
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=DLC_WRITER_VERSION,
        )


def dlc_project_key(dlc_project_code: str, *, lab: DjKey[Lab] | None = None) -> DjKey[DlcProject]:
    """Find a DeepLabCut project by its lab code.

    Args:
        dlc_project_code: Lab code of the project.
        lab: Lab primary key. If omitted, built from ``SCENE_LAB_ID``.

    Returns:
        ``DlcProject`` primary key.

    Raises:
        ValueError: If the code is invalid or not registered in ``lab``, or ``lab`` is
            omitted and ``SCENE_LAB_ID`` is unset.
    """
    lab = lab if lab is not None else lab_key_from_settings()
    code = normalize_code(dlc_project_code, field="dlc_project_code", max_length=128)
    key = lookup_key(DlcProject, {**lab, "dlc_project_code": code})
    if key is None:
        raise ValueError(f"no DeepLabCut project {code!r} in lab {lab['lab_id']!r}")
    return key


def register_project_config(
    path: str | Path,
    *,
    dlc_project: DjKey[DlcProject],
    store: bool = False,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[ProjectConfig]:
    """Register a project's config.yaml: its ``File``, fields and keypoints.

    Args:
        path: A local DeepLabCut config.yaml.
        dlc_project: Existing ``DlcProject`` key.
        store: Also copy the bytes into this deployment's store (``FileContent``).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when this file is already registered for ``dlc_project``; see
            ``DuplicatePolicy``.

    Returns:
        ``ProjectConfig`` primary key.

    Raises:
        ImportError: If ruamel.yaml is not installed (``scene-pipelines[dlc]``).
        ValueError: If ``path`` is not a valid config.yaml, the store is unusable,
            ``deployment`` is omitted and ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists``
            rejects the existing row.
    """
    record = read_project_config(path)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    file = register_file(path, store=store)
    row = {
        "lab_id": dlc_project["lab_id"],
        "dlc_project_id": dlc_project["dlc_project_id"],
        **file,
        "task": record.task,
        "config_date": record.config_date,
        "multianimal": record.multianimal,
        "identity": record.identity,
        "pcutoff": record.pcutoff,
    }
    return insert_tracked_row(
        ProjectConfigRowMeta,
        row,
        payload=asdict(record),
        deployment=deployment_row,
        if_exists=if_exists,
        writer_version=DLC_WRITER_VERSION,
        parts=_keypoint_parts(record),
    )


def _keypoint_parts(record: ConfigRecord) -> dict:
    """Part rows of ``ProjectConfig``, in config order."""
    return {
        ProjectConfig.Bodypart: [
            {"bodypart_index": i, "bodypart": name} for i, name in enumerate(record.bodyparts)
        ],
        ProjectConfig.UniqueBodypart: [
            {"unique_bodypart_index": i, "unique_bodypart": name}
            for i, name in enumerate(record.unique_bodyparts)
        ],
        ProjectConfig.Individual: [
            {"individual_index": i, "individual": name} for i, name in enumerate(record.individuals)
        ],
    }
