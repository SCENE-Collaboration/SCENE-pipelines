"""Sync authority and write role markers (no DB required)."""

from __future__ import annotations

import pytest
from scene_pipelines.core.access_markers import (
    SyncAuthority,
    WriteRole,
    sync_authority_of,
    write_role_of,
)
from scene_pipelines.schemas.files.files import File, Location, Store
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.provenance.row_meta import RowMetaBase
from scene_pipelines.schemas.scene.lab import Lab
from scene_pipelines.schemas.scene.project import Project
from scene_pipelines.schemas.scene.session import Experimenter, Session
from scene_pipelines.schemas.scene.subject import Subject, SubjectKind


def test_catalogs_are_central_and_admin_only():
    for table in (Lab, Project, Store):
        assert sync_authority_of(table) is SyncAuthority.CENTRAL
        assert write_role_of(table) is WriteRole.ADMIN


def test_acquired_rows_are_acquisition_only_and_origin_by_default():
    for table in (Subject, Session, Location):
        assert not hasattr(table, "_sync_authority")
        assert sync_authority_of(table) is SyncAuthority.ORIGIN
        assert write_role_of(table) is WriteRole.ACQUISITION


def test_unmarked_tables_are_unrestricted():
    for table in (Experimenter, SubjectKind):
        assert write_role_of(table) is None
        assert sync_authority_of(table) is SyncAuthority.ORIGIN


def test_deployment_is_shared_and_unrestricted():
    assert sync_authority_of(Deployment) is SyncAuthority.SHARED
    assert write_role_of(Deployment) is None


def test_part_follows_its_master():
    assert not hasattr(Session.Subject, "_write_role")
    assert write_role_of(Session.Subject) is WriteRole.ACQUISITION
    assert sync_authority_of(Session.Subject) is SyncAuthority.ORIGIN


@pytest.mark.parametrize("table", list(RowMetaBase.__subclasses__()))
def test_row_meta_follows_tracked_table(table):
    assert not hasattr(table, "_sync_authority")
    assert not hasattr(table, "_write_role")
    assert sync_authority_of(table) is sync_authority_of(table.tracked_table)
    assert write_role_of(table) is write_role_of(table.tracked_table)


def test_unmarked_class_defaults():
    class LabSpecificLookup:
        """Stands in for a table a lab defines for its own analysis."""

    assert sync_authority_of(LabSpecificLookup) is SyncAuthority.ORIGIN
    assert write_role_of(LabSpecificLookup) is None


def test_file_contents_are_shared_and_unrestricted():
    assert sync_authority_of(File) is SyncAuthority.SHARED
    assert write_role_of(File) is None
