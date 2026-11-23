# Provenance and sync

You rarely need this page to start: the write helpers handle all of it. It explains what they record, and why, for
when rows are compared and synced between databases.

## Deployments

Every database has a deployment id, set once with `SCENE_DEPLOYMENT_ID` and stored in
[`Deployment`][scene_pipelines.schemas.provenance.deployment.Deployment].
See [Choosing a deployment id](setup.md#choosing-a-deployment-id).

## Row stamps

Every helper writes the row and a row-meta stamp next to it (`LabRowMeta`, `SessionRowMeta`, …; see
[`RowMetaBase`][scene_pipelines.schemas.provenance.row_meta.RowMetaBase]). The stamp records:

- which deployment last wrote the row (`deployment_id`, `updated_at`), and which first did
  (`origin_deployment_id`, `created_at`);
- the writer version (`ingestion_version`);
- a `content_hash` of the row's content.

Two databases hold the same entry when the key and the `content_hash` agree; a different hash means the content
differs. [`DuplicatePolicy`](writing-data.md#registering-an-existing-entry-again) uses the same hash to detect changed
content.

The stamp also records the `hash_version` ([`HASH_VERSION`][scene_pipelines.core.hash]) that computed the
hash. A stamp of another hash version counts as missing for `VERIFY`.

Each ingestion package has its own writer version (`SCENE_WRITER_VERSION`, `MOUSE_WRITER_VERSION`, …) in its
`_version.py`. Bump it when a helper in that package changes what it writes or what it hashes; the other packages are
not affected.

## Schema versions

Each schema records the version of its table definitions in a `SchemaVersion` table
([`SchemaVersionTable`][scene_pipelines.core.versioning.SchemaVersionTable]), in the same step that creates the tables.
The write helpers check it against the installed code before their first write
([`assert_schema_compatible`][scene_pipelines.core.versioning.assert_schema_compatible]), so old code never writes into
a newer database, or the reverse.

## Table markers

Two optional markers declare intent for whoever administers a database. Read them with
[`sync_authority_of`][scene_pipelines.core.access_markers.sync_authority_of] and
[`write_role_of`][scene_pipelines.core.access_markers.write_role_of].

!!! note
    This package only defines the markers; it does not enforce them. Grants and sync jobs differ per deployment and
    are the database administrator's to set up.

[`SyncAuthority`][scene_pipelines.core.access_markers.SyncAuthority] names which database holds the truth: `CENTRAL`
(consortium catalogs; the central database has authority), `ORIGIN` (the site that acquired the data has authority),
`SHARED` (append-only; either direction inserts and never overwrites).

[`WriteRole`][scene_pipelines.core.access_markers.WriteRole] restricts INSERT: `ADMIN` or `ACQUISITION`, and a marker
admits only that role. No marker means unrestricted. `Lab` and `Project` are `ADMIN`; `Subject` and `Session` are
`ACQUISITION`. A part follows its master and a row-meta table follows the table it tracks, so those need no marker of
their own. Lab-defined tables need none either.
