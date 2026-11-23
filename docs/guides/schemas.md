# Schemas and the registry

Every shared schema (`scene`, `mouse`, `provenance`, …) registers itself in
[`SCENE_REGISTRY`][scene_pipelines.core.registry] when its module is imported. A lab registers its own
schema in the same registry, so that one call binds them all.

## Activation

Schemas stay unbound by default: importing the tables needs no database. Set `AUTO_ACTIVATE=1` to bind them on import,
or activate them explicitly:

```python
from scene_pipelines.core import SCENE_REGISTRY, activate_schema

schema = SCENE_REGISTRY.make_schema("scene")  # unbound unless AUTO_ACTIVATE
# @schema class Lab ...
SCENE_REGISTRY.activate("scene")  # uses create_tables stored at make_schema
SCENE_REGISTRY.activate_all()  # every registered schema still unbound, dependencies first

# Or bind any dj.Schema without the registry:
activate_schema(schema, "scene")

# A suffix is registered once (make_schema("scene") again raises); reuse it with get
SCENE_REGISTRY.get("scene") is schema
"scene" in SCENE_REGISTRY.schemas  # dict[str, dj.Schema]
```

The database name is the suffix with the `DJ_SCHEMA_PREFIX` in front, e.g. `dev_scene`.
See [`SchemaRegistry`][scene_pipelines.core.registry.SchemaRegistry] for all methods.

## Your lab's own schema

Register the lab's schema under a short name, define its tables, and activate:

```python
import datajoint as dj

from scene_pipelines.core import SCENE_REGISTRY
from scene_pipelines.schemas.scene.session import Session

mylab = SCENE_REGISTRY.make_schema("mylab")


@mylab
class SessionNotes(dj.Manual):
    definition = """
    -> Session
    ---
    rig: varchar(32)
    notes='': varchar(1000)
    """


SCENE_REGISTRY.activate_all()
```

Hang lab tables off the shared rows (`-> Session`, `-> Mouse`) rather than giving the same session a second identity.
A lab with an existing pipeline can link its rows to the shared ones, or migrate them; the
[MLAI tutorial](../tutorials/02_mlai_mouse_ar.ipynb) shows how the Mathis lab does it.

The [Getting started](../tutorials/01_getting_started.ipynb) tutorial walks through this on a local database.
