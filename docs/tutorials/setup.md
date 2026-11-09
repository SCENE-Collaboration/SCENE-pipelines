# Setting up the tutorial notebooks

The tutorial notebooks run against a local database. Each writes only to databases named `tutorial_*` and can be run again.

| Notebook | For |
|---|---|
| [Getting started](01_getting_started.ipynb) | Anyone new: register a lab's mice, sessions and files on the shared tables, add the lab's own tables, query across them. |
| [An existing lab: MLAI and MouseAR](02_mlai_mouse_ar.ipynb) | Labs with an existing pipeline: the Mathis lab's real code for its lab layer, automatic ingestion and legacy tables. |

## New to DataJoint?

These notebooks assume you know DataJoint's basics: schemas, tables, inserts and queries. SCENE pipelines uses
DataJoint 2.2 or later; its official tutorials teach the basics:

| DataJoint tutorial | Covers |
|---|---|
| [First Pipeline](https://docs.datajoint.com/tutorials/basics/01-first-pipeline/) | Tables and dependencies, inserts, and the four core query operations |
| [Schema Design](https://docs.datajoint.com/tutorials/basics/02-schema-design/) | Table tiers, primary keys and dependencies |
| [Data Entry](https://docs.datajoint.com/tutorials/basics/03-data-entry/) | Inserting, updating and deleting |
| [Queries](https://docs.datajoint.com/tutorials/basics/04-queries/) | Restriction, projection, joins and aggregation |
| [Computation](https://docs.datajoint.com/tutorials/basics/05-computation/) | Computed tables and `populate()` |

The [DataJoint tutorials](https://docs.datajoint.com/tutorials/) also include domain examples, such as calcium imaging
and electrophysiology. Its [how-to guides](https://docs.datajoint.com/how-to/) cover single tasks, and its
[concepts](https://docs.datajoint.com/explanation/) cover the data model.

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
