# Changelog

## 0.0.2

### Added

- `files` schema: `File` for files stored outside the database, with stores and locations (#2).
- `video` schema (preliminary): video files, the videos recorded in a session, and processed copies (#16).
- `dlc` schema (preliminary): DeepLabCut projects, the versions of their `config.yaml`, and poses (#15).
- Docs: table definitions and source in the API reference; a guide for videos and DeepLabCut poses (#22).

### Changed

- Tutorial 02 installs MLAI-Base-schemas `v3.0.0rc1` and links SCENE_MouseAR `v0.1.0rc1` (#23).
- README and installation docs: links to the published docs, install from `main` or a tag (#12).

### Fixed

- The row stamps' `hash_version` is declared as `int16`, a DataJoint core type, so DataJoint no longer warns (#21).

The `video` and `dlc` tables may still change before a stable release.

## 0.0.1

- First version, migrated from Base-schemas: the shared `scene`, `mouse` and `provenance` schemas, the ingestion
  helpers, and tutorials 01 and 02 (#1).
