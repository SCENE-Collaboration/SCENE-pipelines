"""Add an Allele to the shared mouse vocabulary (everyday pipeline write).

Any lab adds the alleles and transgenes it uses; no admin role is needed. Names
follow the official MGI nomenclature, so every lab spells an allele the same way.

Not exported from ``scene_pipelines.ingestion``: importing this module registers
the mouse schema, which labs without mice do not need.
"""

from __future__ import annotations

import re
from typing import Any

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.db import atomic, lookup_key
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.mouse._version import MOUSE_WRITER_VERSION
from scene_pipelines.ingestion.mouse.strain import _validate_text
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.schemas.mouse.mouse import Allele
from scene_pipelines.schemas.mouse.row_meta import AlleleRowMeta
from scene_pipelines.schemas.provenance.deployment import Deployment

MGI_ID = re.compile(r"MGI:\d+")


def allele_meta_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Non-key ``Allele`` fields."""
    return {"mgi_id": row.get("mgi_id")}


def ensure_allele(
    allele: DjRow[Allele],
    *,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Allele]:
    """Insert an allele row and stamp the deployment that registered it.

    Args:
        allele: Full allele insert dict: ``allele_name`` in MGI nomenclature and
            optional ``mgi_id`` (``MGI:<digits>``).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when ``allele_name`` is already stored; see ``DuplicatePolicy``.

    Returns:
        Allele primary key ``{allele_name: ...}``.

    Raises:
        ValueError: If ``allele_name`` or ``mgi_id`` is malformed, the name is
            stored under another spelling, the ``mgi_id`` already belongs to
            another allele, ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects the
            existing row.
    """
    name = allele["allele_name"]
    _validate_text(name, field="allele_name", max_length=128)
    mgi_id = allele.get("mgi_id")
    if mgi_id is not None and (not isinstance(mgi_id, str) or not MGI_ID.fullmatch(mgi_id)):
        raise ValueError(f"mgi_id {mgi_id!r} must look like 'MGI:<digits>'")
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()

    with atomic(Allele.connection):
        stored = lookup_key(Allele, {"allele_name": name})
        if stored is not None and stored["allele_name"] != name:
            raise ValueError(
                f"allele {name!r} is already stored as {stored['allele_name']!r}; use that spelling"
            )
        same_mgi = lookup_key(Allele, {"mgi_id": mgi_id}) if mgi_id is not None else None
        if same_mgi is not None and same_mgi != stored:
            raise ValueError(
                f"{mgi_id} is already registered as allele {same_mgi['allele_name']!r}; "
                f"use that allele"
            )
        row = {"allele_name": name, "mgi_id": mgi_id}
        return insert_tracked_row(
            AlleleRowMeta,
            row,
            payload=allele_meta_payload(row),
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=MOUSE_WRITER_VERSION,
        )
