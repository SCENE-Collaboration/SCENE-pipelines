# File store

The bytes of every [`File`][scene_pipelines.schemas.files.files.File] live in a DataJoint store named
`scene-files`, outside the database, at `sha256/<first two hex digits>/<sha256>`. Each machine maps that name
to its own copy in `dj.config["stores"]`; see [`scene_pipelines.ingestion.files.files`][scene_pipelines.ingestion.files.files]
for the configuration.

## Prepare a copy

Run [`init_file_store`][scene_pipelines.ingestion.files.admin.init_file_store] once, by hand, on a machine
configured for the copy. It writes `scene-files.json` at the root; `register_file` and `record_file` refuse a
store without it.

```python
from scene_pipelines.ingestion.files import admin

admin.init_file_store()               # a copy that already holds this database's files, or an empty database
admin.init_file_store(new_copy=True)  # a new, empty copy that a transfer job will fill
```

It refuses a copy that is already prepared, and a place that holds none of a few files the database records
(not mounted, or a wrong location). Never call it from an ingestion script.

## On disk

- Mount the share one level above the store's folder (store at `/mnt/labserver/scene-files`, share at
  `/mnt/labserver`): while it is not mounted, the folder does not exist and every helper refuses it.
- If several users write, give the root folder their group and the setgid bit before `init_file_store`, which
  then creates `sha256/00` to `sha256/ff` group-writable:

  ```bash
  chgrp scene-writers /mnt/labserver/scene-files
  chmod 2775 /mnt/labserver/scene-files
  ```

## On S3

- Preferably ensure a lifecycle rule that aborts incomplete multipart uploads under the store's prefix (an interrupted upload
  otherwise leaves hidden parts that take up space):

  ```json
  {"Rules": [{"ID": "abort-incomplete-uploads", "Status": "Enabled",
              "Filter": {"Prefix": "scene-files/"},
              "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}}]}
  ```

  set with `aws s3api put-bucket-lifecycle-configuration`. MinIO cleans up stale uploads by itself.
- put-only credentials for writers (the helpers never delete on S3), read-only ones for readers.

Keys go in `.secrets/stores.scene-files.access_key` and `.secrets/stores.scene-files.secret_key`, never in the
database. Clients need `pip install "scene-pipelines[s3]"`.

## Copies and sync

- Keep copies in step with `rclone copy --checksum`, never `rclone sync`: files are never deleted.
- Bytes before rows: a database that receives `File` rows reads them from its own copy, so the transfer must
  finish before the rows are synced.
- DataJoint's garbage collector never touches this store; nothing deletes from it.
- Audit now and then with [`verify_file`][scene_pipelines.ingestion.files.files.verify_file], which re-reads a
  file and checks its SHA-256.
