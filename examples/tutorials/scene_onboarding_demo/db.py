"""Connect to the tutorial database and bind every schema the demo uses."""

from __future__ import annotations

import tutorial_utils

SCHEMA_PREFIX = "tutorial_onboarding_"


def connect() -> None:
    """Connect with ``tutorial_utils.connect``, then create and bind the shared and lab schemas."""
    tutorial_utils.connect(prefix=SCHEMA_PREFIX)

    import datajoint as dj

    dj.config["loglevel"] = "ERROR"  # quiets the notes on native types while declaring

    # Imported for their tables: the shared helpers and the lab's own schemas.
    import scene_pipelines.ingestion.dlc  # noqa: F401
    import scene_pipelines.ingestion.mouse  # noqa: F401
    import scene_pipelines.ingestion.video  # noqa: F401
    from scene_pipelines.core import SCENE_REGISTRY

    import scene_onboarding_demo.schemas  # noqa: F401

    SCENE_REGISTRY.activate_all()


def drop_demo_schemas() -> list[str]:
    """Drop every database of this tutorial; restart the kernel afterwards."""
    return tutorial_utils.drop_tutorial_schemas(SCHEMA_PREFIX)
