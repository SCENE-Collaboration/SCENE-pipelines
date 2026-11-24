"""Read the fields ``ProjectConfig`` stores from a DeepLabCut config.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ConfigRecord:
    """A config.yaml as ``ProjectConfig`` stores it.

    Attributes:
        task: ``Task``.
        config_date: ``date``, e.g. ``Oct30``.
        multianimal: ``multianimalproject``.
        identity: ``identity``; ``False`` when unset and in single-animal projects.
        pcutoff: ``pcutoff``.
        bodyparts: Bodyparts on each animal, in config order (``multianimalbodyparts`` in
            multi-animal projects).
        unique_bodyparts: ``uniquebodyparts``; multi-animal only.
        individuals: ``individuals``; multi-animal only.
    """

    task: str
    config_date: str
    multianimal: bool
    identity: bool
    pcutoff: float
    bodyparts: tuple[str, ...]
    unique_bodyparts: tuple[str, ...]
    individuals: tuple[str, ...]


def read_project_config(path: str | Path) -> ConfigRecord:
    """Read a DeepLabCut config.yaml.

    Raises:
        ImportError: If ruamel.yaml is not installed.
        ValueError: If ``path`` is not a file, or a field is missing or malformed.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    try:
        from ruamel.yaml import YAML
    except ImportError as exc:
        raise ImportError(
            'reading DeepLabCut configs needs ruamel.yaml: pip install "scene-pipelines[dlc]"'
        ) from exc

    config = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"{path} is not a DeepLabCut config: not a mapping")

    multianimal = config.get("multianimalproject") or False
    if not isinstance(multianimal, bool):
        raise ValueError(f"multianimalproject must be true or false, not {multianimal!r}")

    if multianimal:
        bodyparts = _names(config, "multianimalbodyparts")
        unique_bodyparts = _names(config, "uniquebodyparts")
        individuals = _names(config, "individuals")
        identity = config.get("identity") or False
        if not isinstance(identity, bool):
            raise ValueError(f"identity must be true, false or unset, not {identity!r}")
    else:
        bodyparts = _names(config, "bodyparts")
        unique_bodyparts, individuals, identity = (), (), False
    if not bodyparts:
        raise ValueError(f"{path} declares no bodyparts")

    pcutoff = config.get("pcutoff")
    if isinstance(pcutoff, bool) or not isinstance(pcutoff, (int, float)):
        raise ValueError(f"pcutoff must be a number, not {pcutoff!r}")

    return ConfigRecord(
        task=_text(config, "Task", max_length=128),
        config_date=_text(config, "date", max_length=16),
        multianimal=multianimal,
        identity=identity,
        pcutoff=float(pcutoff),
        bodyparts=bodyparts,
        unique_bodyparts=unique_bodyparts,
        individuals=individuals,
    )


def _text(config: dict[str, Any], field: str, *, max_length: int) -> str:
    """A required field as text, at most ``max_length`` characters."""
    value = config.get(field)
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is missing")
    text = str(value)
    if len(text) > max_length:
        raise ValueError(f"{field} {text!r} is longer than {max_length} characters")
    return text


def _names(config: dict[str, Any], field: str) -> tuple[str, ...]:
    """A list of distinct, non-empty names of at most 64 characters; unset is empty."""
    values = config.get(field) or []
    if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
        raise ValueError(f"{field} must be a list of names, not {values!r}")
    too_long = [v for v in values if len(v) > 64]
    if too_long:
        raise ValueError(f"{field} has names longer than 64 characters: {too_long}")
    repeated = sorted({v for v in values if values.count(v) > 1})
    if repeated:
        raise ValueError(f"{field} lists {repeated} more than once")
    return tuple(values)
