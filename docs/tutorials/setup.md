# Setting up the tutorial notebooks

The tutorial notebooks run against a local database. Each writes only to databases named `tutorial_*` and can be run again.

| Notebook | For |
|---|---|
| [Getting started](01_getting_started.ipynb) | Anyone new: register a lab's mice, sessions and files on the shared tables, add the lab's own tables, query across them. |
| [An existing lab: MLAI and MouseAR](02_mlai_mouse_ar.ipynb) | Labs with an existing pipeline: the Mathis lab's real code for its lab layer, automatic ingestion and legacy tables. |

## Running them locally

From the repository root:

```bash
pip install -e .
make init        # once: creates .env
make db_up       # starts MySQL
```

The notebooks are in [`examples/tutorials/`](https://github.com/SCENE-Collaboration/SCENE-pipelines/tree/dev/examples/tutorials).
Open them from that folder, so that `tutorial_utils` can be imported.
`tutorial_utils.drop_tutorial_schemas()` removes the tutorial databases to start over.

## Running them on Google Colab

Each notebook has an **Open in Colab** badge at the top. On Colab, run the first code cell: it installs MySQL and the
package in the Colab machine. Nothing is needed on your own computer, and the database is gone when the
Colab session ends.
