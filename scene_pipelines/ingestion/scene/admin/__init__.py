"""Admin catalog writes (Lab, Project, …).

Pipeline roles should SELECT these tables only; use these helpers with an
admin DB role. ``Lab`` and ``Project`` are marked ``WriteRole.ADMIN``.
"""

from scene_pipelines.ingestion.scene.admin.lab import ensure_lab
from scene_pipelines.ingestion.scene.admin.project import ensure_project

__all__ = ["ensure_lab", "ensure_project"]
