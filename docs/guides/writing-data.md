# Writing data

Write to the shared tables through the helpers in `scene_pipelines.ingestion`, not with `insert1`.
The helpers check the input, mint ids, write the rows that belong together in one transaction, and record a
[row stamp](provenance.md#row-stamps) next to each row. Your lab's own tables are written with plain DataJoint.

## Catalogs: labs and projects

[`Lab`][scene_pipelines.schemas.scene.lab.Lab] and [`Project`][scene_pipelines.schemas.scene.project.Project] are
catalogs shared across the collaboration. An administrator creates them with the helpers in
`scene_pipelines.ingestion.scene.admin`; a lab usually finds its rows already there.

- [`ensure_lab`][scene_pipelines.ingestion.scene.admin.lab.ensure_lab]: insert a lab row, return its key
- [`ensure_project`][scene_pipelines.ingestion.scene.admin.project.ensure_project]: insert a project row, return its key

[`Experimenter`][scene_pipelines.schemas.scene.session.Experimenter] is a plain lookup of pseudonymous codes per lab;
insert into it directly.

## Subjects and sessions

[`Subject`][scene_pipelines.schemas.scene.subject.Subject] and
[`Session`][scene_pipelines.schemas.scene.session.Session] are everyday writes. They are inserted locally by one lab
and later shared with the consortium.

- [`register_subject`][scene_pipelines.ingestion.scene.subject.register_subject]: register a subject by code, return its key
- [`register_mouse`][scene_pipelines.ingestion.mouse.mouse.register_mouse]: register a mouse by code (its `Subject` and
  [`Mouse`][scene_pipelines.schemas.mouse.mouse.Mouse] row), return its key
- [`ensure_strain`][scene_pipelines.ingestion.mouse.strain.ensure_strain]: add a background strain to the shared vocabulary
- [`register_session`][scene_pipelines.ingestion.scene.session.register_session]: register a session by code, linking
  **existing** subject keys (may be empty)

Subjects and sessions are identified by a code the lab chooses (`subject_code`, `session_code`), unique within the lab.
The globally unique `subject_id` / `session_id` is minted by the helper (UUID4) the first time a code is registered.
Registering the same code again reuses the stored id, so re-running an ingestion does not create duplicates.

Codes are shared with the consortium, so they must be **pseudonyms**: never a real name, initials, birth date or other
identifying information. The helpers accept only ASCII letters, digits, `.`, `_` and `-` (no spaces), which rejects
free-text names but cannot catch every identifying code.

```python
from datetime import date
from scene_pipelines.ingestion import register_session, register_subject

lab = {"lab_id": "humanlab"}
participant = register_subject("P042", "human", lab=lab)
register_session("gaze-session-015", date(2026, 5, 1), lab=lab, subjects=[participant])
```

Mice are registered with `register_mouse`, which also writes their `Mouse` row:

```python
from scene_pipelines.ingestion.mouse import register_mouse

lab = {"lab_id": "mlai"}
mouse = register_mouse("mouse-042", "F", lab=lab)
register_session(
    "mousear-session-015",
    date(2026, 5, 1),
    lab=lab,
    subjects=[mouse],
    project={"project_name": "gaze_v1"},
)
```

## Several writes at once

Each helper is atomic and joins a transaction that is already open. To make several registrations all-or-nothing,
wrap them in [`atomic`][scene_pipelines.core.db.atomic]:

```python
from scene_pipelines.core import atomic
from scene_pipelines.schemas.scene.session import Session

with atomic(Session.connection):
    subjects = [register_mouse(code, "F", lab=lab) for code in ("mouse-043", "mouse-044")]
    register_session("mousear-session-016", date(2026, 5, 2), lab=lab, subjects=subjects)
```

### Design rule: one transaction per write

A function that writes to more than one table performs all of its writes inside a single transaction (`atomic`).
Nothing else happens inside it: no file reading, no computation, no schema activation. Read and validate the input
first, then write. This keeps a failed write from leaving partial rows, and keeps transactions (and their locks) short.
The write helpers follow this rule; ingestion code built on them (e.g. a manifest loader) should too.

## Finding a row by its lab code

Tables are keyed by the minted id, not by the lab's code.
[`subject_key`][scene_pipelines.ingestion.scene.subject.subject_key] and
[`session_key`][scene_pipelines.ingestion.scene.session.session_key] look up the key of a code within a lab; use it as
a restriction:

```python
from scene_pipelines.ingestion import session_key, subject_key
from scene_pipelines.schemas.mouse.mouse import Mouse

mouse = Mouse & subject_key("mouse-042", lab={"lab_id": "mlai"})  # restriction
mouse.fetch1()  # the row as a dict
session_key("mousear-session-015", lab={"lab_id": "mlai"})
```

With `SCENE_LAB_ID=mlai` set, `lab` can be omitted in these lookups: `subject_key("mouse-042")`.
The write helpers (`register_*`) always take an explicit `lab`.

!!! warning
    Don't restrict `Mouse` by `subject_code` directly. It is a column of `Subject`, not `Mouse`, so DataJoint ignores
    it and returns every mouse:

    ```python
    Mouse & {"subject_code": "mouse-042"}  # wrong: returns every mouse
    ```

## Registering an existing entry again

The helpers take `if_exists: DuplicatePolicy` to control what happens when the entry already exists (same primary key
for `ensure_*`, same code within the lab for `register_*`). Unlike DataJoint's `skip_duplicates` / `replace`,
[`DuplicatePolicy`][scene_pipelines.ingestion.provenance.row_meta.DuplicatePolicy] compares the content hash in the
stored [row stamp](provenance.md#row-stamps), so it detects changed content:

| Policy | When the entry already exists |
|---|---|
| `REJECT` (default for `ensure_*`) | raise `ValueError` |
| `SKIP` | leave row and stamp untouched |
| `VERIFY` (default for `register_*`) | leave untouched when the stamp hash matches; raise when it differs or no stamp exists |
| `OVERWRITE` | overwrite the row in place as an insert would store it (omitted fields reset to their default), and its stamp (sessions: also their subject links); warn when the hash changed |

```python
from scene_pipelines.ingestion.scene import admin
from scene_pipelines.ingestion.provenance import DuplicatePolicy

admin.ensure_lab({"lab_id": "mlai", "lab_name": "Mathis Lab"}, if_exists=DuplicatePolicy.VERIFY)
```
