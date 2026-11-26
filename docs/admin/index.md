# Administration

For whoever runs a SCENE deployment: its database server, its file stores, its users. Writing data is
covered in the [guides](../guides/writing-data.md).

Setting up a deployment:

1. A database, with a deployment id: [Setup and configuration](../guides/setup.md).
2. Users and their rights, following the [access markers](../guides/provenance.md).
3. Catalog rows (labs, projects), with the helpers in `scene_pipelines.ingestion.scene.admin`.
4. A copy of the file store, if the deployment holds files: [File store](file-store.md).
