"""SCENE shared identity + session graph (Lab, Subject, Project, Session, …).

Placeholder scientific tables — definitions are subject to change.

DDL: ``SCENE_SCHEMA_VERSION`` / ``SchemaVersion``.
Row write provenance lives in ``scene_pipelines.schemas.provenance``
(e.g. ``Deployment``, ``SessionRowMeta``, ``LabRowMeta``, ``ProjectRowMeta``, ``SubjectRowMeta``).
"""

from scene_pipelines.schemas.scene._schema import SCENE_SCHEMA_VERSION

__all__ = ["SCENE_SCHEMA_VERSION"]
