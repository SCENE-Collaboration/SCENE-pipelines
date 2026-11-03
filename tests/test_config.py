"""Unit tests for core config (no database)."""

import pytest
from scene_pipelines.core import load_settings


def test_load_settings_default(monkeypatch):
    monkeypatch.delenv("DJ_SCHEMA_PREFIX", raising=False)
    monkeypatch.delenv("AUTO_ACTIVATE", raising=False)
    monkeypatch.delenv("SCENE_DEPLOYMENT_ID", raising=False)
    monkeypatch.delenv("SCENE_DEPLOYMENT_LABEL", raising=False)
    monkeypatch.delenv("SCENE_LAB_ID", raising=False)
    monkeypatch.delenv("SCENE_STORE", raising=False)
    settings = load_settings()
    assert settings.prefix == ""
    assert settings.auto_activate is False
    assert settings.deployment_id is None
    assert settings.deployment_label == ""
    assert settings.lab_id is None
    assert settings.store is None


def test_load_settings_prefix_and_auto_activate(monkeypatch):
    monkeypatch.setenv("DJ_SCHEMA_PREFIX", "dev_")
    monkeypatch.setenv("AUTO_ACTIVATE", "true")
    settings = load_settings()
    assert settings.prefix == "dev_"
    assert settings.auto_activate is True
    assert settings.db_name("scene") == "dev_scene"


def test_load_settings_deployment(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", " mlai-prod ")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", " MLAI production ")
    settings = load_settings()
    assert settings.deployment_id == "mlai-prod"
    assert settings.deployment_label == "MLAI production"


def test_schema_prefix_rejects_invalid(monkeypatch):
    monkeypatch.setenv("DJ_SCHEMA_PREFIX", "bad-prefix!")
    with pytest.raises(ValueError, match="Invalid DJ_SCHEMA_PREFIX"):
        load_settings()


def test_schema_prefix_requires_trailing_underscore(monkeypatch):
    monkeypatch.setenv("DJ_SCHEMA_PREFIX", "dev")
    with pytest.raises(ValueError, match="must end with '_'"):
        load_settings()


def test_db_name_rejects_empty_suffix(monkeypatch):
    monkeypatch.delenv("DJ_SCHEMA_PREFIX", raising=False)
    with pytest.raises(ValueError, match="non-empty"):
        load_settings().db_name("")


def test_lab_key_from_settings(monkeypatch):
    from scene_pipelines.core.config import lab_key_from_settings

    monkeypatch.setenv("SCENE_LAB_ID", " mlai ")
    assert load_settings().lab_id == "mlai"
    assert lab_key_from_settings() == {"lab_id": "mlai"}
    monkeypatch.delenv("SCENE_LAB_ID")
    with pytest.raises(ValueError, match="SCENE_LAB_ID"):
        lab_key_from_settings()
