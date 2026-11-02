# Setup and configuration

## Installation

```bash
pip install -e ".[dev]"   # development, from a clone
pip install .             # usage
```

From GitHub (`dev` can be a commit hash or branch):

```bash
pip install "git+ssh://git@github.com/SCENE-Collaboration/SCENE-pipelines.git@dev"
pip install "git+https://github.com/SCENE-Collaboration/SCENE-pipelines.git@dev"
```

Build a wheel:

```bash
pip install build
python -m build .
pip install dist/scene_pipelines-*.whl
```

## A local database (Docker)

```bash
make init          # once: copy .env.example → .env, then edit as needed
make db_up         # MySQL only
make build_all     # or: MySQL and a client container
make up_all
make client_bash
```

The host port for MySQL is `MYSQL_PUBLISH_PORT` in `.env` (default `3306`).

!!! warning
    MySQL applies `MYSQL_ROOT_PASSWORD` only when the data directory (`DATABASE_MOUNT`) is first initialized.
    If you change it in `.env` afterwards, the `db` container never becomes healthy: change the password inside MySQL,
    or remove the data directory to start from an empty database.

## Configuration

SCENE pipelines reads its settings from environment variables ([`load_settings`][scene_pipelines.core.config.load_settings]):

| Variable | Meaning |
|---|---|
| `DJ_SCHEMA_PREFIX` | Prefix for database names, including the trailing `_`, e.g. `dev_` → `dev_scene` |
| `AUTO_ACTIVATE` | If truthy, schemas bind to the database on import; see [Schemas and the registry](schemas.md) |
| `SCENE_DEPLOYMENT_ID` | Stable id of this database; the default `deployment` for all write helpers |
| `SCENE_DEPLOYMENT_LABEL` | Optional human label, stored on the `Deployment` row at the first write |
| `SCENE_LAB_ID` | Optional lab of this deployment; the default `lab` for `subject_key` / `session_key` (not for writes) |

The DataJoint connection itself (host, user, password) is configured as usual for DataJoint.

### Choosing a deployment id

Set `SCENE_DEPLOYMENT_ID` once per database (optional `SCENE_DEPLOYMENT_LABEL`). The write helpers read it when
`deployment` is not passed explicitly, and insert the matching
[`Deployment`][scene_pipelines.schemas.provenance.deployment.Deployment] row on first use.

The id is a stable, opaque token: pick a short slug that names the lab and the role of the database, e.g. `mlai-prod`
for the production database of the Mathis Lab of Adaptive Intelligence, or `mlai-dev-jaap` for a private development
copy. Do not derive it from a hostname or the schema prefix; those may change, the id must not. The label is free text
for humans. It is stored by the first write and should not be changed later (ignored with a warning).
