# SCENE pipelines

[![Docs](https://img.shields.io/badge/docs-scene--collaboration.github.io-0B5D73)](https://scene-collaboration.github.io/SCENE-pipelines/)
[![Docs build](https://github.com/SCENE-Collaboration/SCENE-pipelines/actions/workflows/docs.yml/badge.svg)](https://github.com/SCENE-Collaboration/SCENE-pipelines/actions/workflows/docs.yml)
[![Release](https://img.shields.io/github/v/tag/SCENE-Collaboration/SCENE-pipelines?label=release)](https://github.com/SCENE-Collaboration/SCENE-pipelines/tags)

**Documentation: [scene-collaboration.github.io/SCENE-pipelines](https://scene-collaboration.github.io/SCENE-pipelines/)**

Shared [DataJoint](https://datajoint.com/) tables for the labs of SCENE, and the Python helpers that write to them.
Every lab registers its labs, subjects, sessions and files in the same tables, keeps its own tables next to them, and
links the two by key.

Migrated with full history from [Base-schemas](https://github.com/SCENE-Collaboration/Base-schemas),
where the earlier review discussions live.

> [!NOTE]
> The table definitions are placeholders and may still change.

## Documentation

The [documentation](https://scene-collaboration.github.io/SCENE-pipelines/) is built from [`docs/`](docs/) with
MkDocs; `mkdocs serve` serves it locally (see [Development](https://scene-collaboration.github.io/SCENE-pipelines/development/)).
Good places to start:

- [Introduction](https://scene-collaboration.github.io/SCENE-pipelines/introduction/): the ideas behind the shared
  tables (layers, lab codes and ids, files).
- [Getting started](https://scene-collaboration.github.io/SCENE-pipelines/tutorials/01_getting_started/): a notebook
  that runs on a local database. New to DataJoint? See
  [the DataJoint tutorials to start with](https://scene-collaboration.github.io/SCENE-pipelines/tutorials/setup/#new-to-datajoint).
- Guides: [setup and configuration](https://scene-collaboration.github.io/SCENE-pipelines/guides/setup/),
  [writing data](https://scene-collaboration.github.io/SCENE-pipelines/guides/writing-data/),
  [schemas and the registry](https://scene-collaboration.github.io/SCENE-pipelines/guides/schemas/),
  [provenance and sync](https://scene-collaboration.github.io/SCENE-pipelines/guides/provenance/).
- [API reference](https://scene-collaboration.github.io/SCENE-pipelines/reference/scene_pipelines/): every table and
  helper, from the docstrings.

[An existing lab: MLAI and MouseAR](https://scene-collaboration.github.io/SCENE-pipelines/tutorials/02_mlai_mouse_ar/)
shows a real lab pipeline (Mathis lab, Mouse AR) on the shared tables.

## Quickstart

### Quick installation
To use the package, install the latest version on `main` directly from GitHub:

```bash
pip install "scene-pipelines @ git+https://github.com/SCENE-Collaboration/SCENE-pipelines.git"
```

### Editable install
Or clone the repository and install an editable version:

```bash
git clone https://github.com/SCENE-Collaboration/SCENE-pipelines.git
cd SCENE-pipelines
pip install -e ".[dev]"
```

To run the unit tests (no database needed):

```bash
make test
```

To set up a local database and run the database tests against it:

```bash
make init          # once: copy .env.example → .env, then edit as needed
make db_up         # local MySQL in Docker
make test-db       # database tests (also starts the database if needed)
```

### Tutorials and guides

- See [Setup and configuration](https://scene-collaboration.github.io/SCENE-pipelines/guides/setup/) for a guide on setting up the environment variables and the Docker client container.
- Run our notebook [Getting started](https://scene-collaboration.github.io/SCENE-pipelines/tutorials/01_getting_started/) to try hands-on.

## Acknowledgments

We thank Prof. Mackenzie Mathis, Dr. Tanmay Nath, Dr. Gary Kane, and Dr. Mariia Popova for their early contributions to this codebase, which helped establish the foundation of the shared schemas used across pipelines.
