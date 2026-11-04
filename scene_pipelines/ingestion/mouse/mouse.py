"""Register a Mouse together with its Subject (everyday pipeline write).

Not exported from ``scene_pipelines.ingestion``: importing this module registers
the mouse schema, which labs without mice do not need.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from scene_pipelines.core.config import deployment_row_from_settings
from scene_pipelines.core.db import atomic, lookup_key
from scene_pipelines.core.types import DjKey, DjRow
from scene_pipelines.ingestion.mouse._version import MOUSE_WRITER_VERSION
from scene_pipelines.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from scene_pipelines.ingestion.scene.subject import _register_subject
from scene_pipelines.schemas.mouse.mouse import Allele, Mouse, Strain
from scene_pipelines.schemas.mouse.row_meta import MouseRowMeta
from scene_pipelines.schemas.provenance.deployment import Deployment
from scene_pipelines.schemas.scene.lab import Lab
from scene_pipelines.schemas.scene.subject import SubjectKind

ZYGOSITIES = ("hom", "het", "hemi", "unknown")


def mouse_meta_payload(
    row: dict[str, Any], alleles: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Non-key ``Mouse`` fields and alleles that should affect ``content_hash``.

    ``alleles`` is left out when empty, so mice without alleles keep their hash.
    """
    date_of_birth = row.get("date_of_birth")
    payload = {
        "sex": row["sex"],
        "date_of_birth": None if date_of_birth is None else str(date_of_birth),
        "strain_name": row.get("strain_name"),
        "genotype": row.get("genotype"),
    }
    if alleles:
        payload["alleles"] = sorted([name, zygosity] for name, zygosity in alleles.items())
    return payload


def _stored_alleles(alleles: Mapping[str, str]) -> dict[str, str]:
    """Map each allele to its stored spelling; reject unknown alleles and zygosities."""
    stored = {}
    for name, zygosity in alleles.items():
        if zygosity not in ZYGOSITIES:
            raise ValueError(f"zygosity of {name!r} must be one of {ZYGOSITIES}, not {zygosity!r}")
        key = lookup_key(Allele, {"allele_name": name})
        if key is None:
            raise ValueError(f"unknown allele {name!r}; add it with ensure_allele")
        if key["allele_name"] in stored:
            raise ValueError(f"allele {key['allele_name']!r} is listed more than once")
        stored[key["allele_name"]] = zygosity
    return stored


def register_mouse(
    subject_code: str,
    sex: str,
    *,
    lab: DjKey[Lab],
    date_of_birth: date | None = None,
    strain: DjKey[Strain] | None = None,
    genotype: str | None = None,
    alleles: Mapping[str, str] | None = None,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Mouse]:
    """Register a mouse by its lab code: the ``Subject`` and its ``Mouse`` row.

    Args:
        subject_code: Pseudonymous code, unique within ``lab``.
        sex: ``"M"``, ``"F"`` or ``"U"`` (unknown).
        lab: Existing lab primary key, e.g. ``{"lab_id": "mlai"}``.
        date_of_birth: Optional date of birth.
        strain: Optional existing ``Strain`` key (background strain), e.g.
            ``{"strain_name": "C57BL/6J"}``; add a new one first with ``ensure_strain``.
        genotype: Optional free-text genotype note. For queries, use ``alleles``.
        alleles: Optional ``{allele_name: zygosity}`` of existing ``Allele`` rows,
            zygosity ``"hom"``, ``"het"``, ``"hemi"`` or ``"unknown"``; add a
            new allele first with ``ensure_allele``. Written to ``Mouse.Genotype``.
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy applied to the subject and to the mouse row when
            already registered; see ``DuplicatePolicy``. ``OVERWRITE`` also
            replaces the alleles.

    Returns:
        Mouse primary key ``{subject_id: ...}`` (same as the subject's).

    Raises:
        ValueError: If ``subject_code`` is not a valid code, the code belongs
            to a subject of another kind, ``strain`` or an allele does not
            exist, a zygosity is invalid,
            ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects an
            existing subject or mouse.
    """
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    strain_name = None
    if strain is not None:
        stored_strain = lookup_key(Strain, strain)
        if stored_strain is None:
            raise ValueError(f"unknown strain {strain['strain_name']!r}; add it with ensure_strain")
        strain_name = stored_strain[
            "strain_name"
        ]  # stored spelling (names match case-insensitively)

    with atomic(Mouse.connection):
        alleles = _stored_alleles(alleles or {})
        # Refuses a code of another kind, under any policy, before anything is written.
        subject = _register_subject(
            subject_code,
            SubjectKind.MOUSE["subject_kind"],
            lab=lab,
            deployment=deployment_row,
            if_exists=if_exists,
        )
        row = {
            **subject,
            "sex": sex,
            "date_of_birth": date_of_birth,
            "strain_name": strain_name,
            "genotype": genotype,
        }
        return insert_tracked_row(
            MouseRowMeta,
            row,
            payload=mouse_meta_payload(row, alleles),
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=MOUSE_WRITER_VERSION,
            parts={
                Mouse.Genotype: [
                    {"allele_name": name, "zygosity": zygosity}
                    for name, zygosity in alleles.items()
                ]
            },
        )
