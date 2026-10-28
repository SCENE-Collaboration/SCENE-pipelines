"""Admin catalog write (Store).

Pipeline roles should SELECT ``Store`` only; use this helper with an admin DB
role. ``Store`` is marked ``WriteRole.ADMIN``.
"""

from __future__ import annotations

from typing import Any

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.files._version import FILES_WRITER_VERSION
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.schemas.files.files import Store
from scene_pipelines.schemas.files.row_meta import StoreRowMeta
from scene_pipelines.schemas.provenance.deployment import Deployment


def store_meta_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Non-key ``Store`` fields."""
    return {
        "store_kind": row["store_kind"],
        "lab_id": row.get("lab_id"),
        "store_details": row.get("store_details") or "",
    }


def ensure_store(
    store: DjRow[Store],
    *,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.REJECT,
) -> DjKey[Store]:
    """Insert a store row and stamp the deployment that registered it.

    Args:
        store: Full store insert dict: ``store_name``, ``store_kind`` (``s3`` or
            ``file``), optional ``lab_id`` (the lab that runs it) and ``store_details``.
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when ``store_name`` is already stored; see ``DuplicatePolicy``.

    Returns:
        Store primary key ``{store_name: ...}``.
    """
    return insert_tracked_row(
        StoreRowMeta,
        store,
        payload=store_meta_payload(store),
        deployment=deployment if deployment is not None else deployment_row_from_settings(),
        if_exists=if_exists,
        writer_version=FILES_WRITER_VERSION,
    )
