# SCENE pipelines

Shared [DataJoint](https://datajoint.com/) tables for the labs of SCENE, and the Python helpers that write to them.
Every lab registers its labs, subjects, sessions and files in the same tables, keeps its own tables next to them, and
links the two by key.

Migrated with full history from [Base-schemas](https://github.com/SCENE-Collaboration/Base-schemas),
where the earlier review discussions live.

> [!NOTE]
> The table definitions are placeholders and may still change.

## Documentation

The documentation is built from [`docs/`](docs/) with MkDocs. Good places to start:

- [Introduction](docs/introduction.md): the ideas behind the shared tables (layers, lab codes and ids, files).
- [Getting started](examples/tutorials/01_getting_started.ipynb): a notebook that runs on a local database.
- Guides: [setup and configuration](docs/guides/setup.md), [writing data](docs/guides/writing-data.md),
  [schemas and the registry](docs/guides/schemas.md), [provenance and sync](docs/guides/provenance.md).
- [Development](docs/development.md): tests and building the documentation.

[An existing lab: MLAI and MouseAR](examples/tutorials/02_mlai_mouse_ar.ipynb) shows a real lab pipeline (Mathis lab,
Mouse AR) on the shared tables.

## Quickstart

```bash
pip install -e ".[dev]"
make init          # once: copy .env.example → .env, then edit as needed
make db_up         # local MySQL in Docker
make test          # unit tests
```

Then work through [Getting started](examples/tutorials/01_getting_started.ipynb). See [Setup and configuration](docs/guides/setup.md) for installing from GitHub, the environment variables, and the
Docker client container.

## Acknowledgments

We thank Prof. Mackenzie Mathis, Dr. Tanmay Nath, Dr. Gary Kane, and Dr. Mariia Popova for their early contributions to this codebase, which helped establish the foundation of the shared schemas used across pipelines.
