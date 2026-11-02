# Tutorials

Notebooks that run against a local database. Each writes only to databases named `tutorial_*` and can be run again.

| Notebook | For |
|---|---|
| [Getting started](01_getting_started.ipynb) | Anyone new: register a lab's mice, sessions and files on the shared tables, add the lab's own tables, query across them. |

## Running them

From the repository root:

```bash
pip install -e .
make init        # once: creates .env
make db_up       # starts MySQL
```

Then open a notebook from this folder (`docs/tutorials/`), so that `tutorial_utils` can be imported.
`tutorial_utils.drop_tutorial_schemas()` removes the tutorial databases to start over.
