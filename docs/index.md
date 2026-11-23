# SCENE pipelines

Shared [DataJoint](https://datajoint.com/) tables for the labs of SCENE, and the Python helpers that write to them.
Every lab registers its labs, subjects, sessions and files in the same tables, keeps its own tables next to them, and
links the two by key.

!!! note
    The table definitions are placeholders and may still change.

## Where to start

| You want to | Read |
|---|---|
| understand what this is and how the pieces fit | [Introduction](introduction.md) |
| try it on a local database | [Getting started](tutorials/01_getting_started.ipynb) |
| install it and configure a database | [Setup and configuration](guides/setup.md) |
| write your lab's data to the shared tables | [Writing data](guides/writing-data.md) |
| add your lab's own tables | [Schemas and the registry](guides/schemas.md) |
| understand row stamps, versions and table markers | [Provenance and sync](guides/provenance.md) |
| look up a table or helper | API reference |

## The package

| Package | Contents |
|---|---|
| [`scene_pipelines.schemas`][scene_pipelines.schemas] | table definitions: `scene` (lab, project, subject, session), `mouse`, `provenance` |
| [`scene_pipelines.ingestion`][scene_pipelines.ingestion] | the helpers that write to the shared tables (`register_session`, …), in packages that mirror the schemas |
| [`scene_pipelines.core`][scene_pipelines.core] | the schema registry, settings, transactions, versioning and table markers |

SCENE pipelines was migrated with full history from
[Base-schemas](https://github.com/SCENE-Collaboration/Base-schemas), where the earlier review discussions live.
