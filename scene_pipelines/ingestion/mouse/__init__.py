"""Write helpers for the mouse tables (Strain, Allele, Mouse).

Importing this package registers the mouse schema, so it is not re-exported
from ``scene_pipelines.ingestion``: labs without mice never import it.
"""

from scene_pipelines.ingestion.mouse._version import MOUSE_WRITER_VERSION
from scene_pipelines.ingestion.mouse.allele import ensure_allele
from scene_pipelines.ingestion.mouse.mouse import register_mouse
from scene_pipelines.ingestion.mouse.strain import ensure_strain

__all__ = ["MOUSE_WRITER_VERSION", "ensure_allele", "ensure_strain", "register_mouse"]
