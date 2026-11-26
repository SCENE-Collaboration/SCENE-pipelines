# Examples

Runnable examples. They are not installed or tested with the package.

| Folder | What |
|---|---|
| [`tutorials/`](tutorials/) | Notebooks on a local database, also shown in the documentation. Run them from that folder. |

| Notebook | For |
|---|---|
| [Getting started](tutorials/01_getting_started.ipynb) | A new lab: mice, sessions and files on the shared tables, the lab's own tables, queries. |
| [Onboarding a lab with DeepLabCut](tutorials/02_scene_onboarding_demo.ipynb) | A lab's pipeline end to end on real DeepLabCut data: shared video and pose tables, the lab's own tables, computed analyses. Its lab code is in [`tutorials/scene_onboarding_demo/`](tutorials/scene_onboarding_demo/). |
| [An existing lab: MLAI and MouseAR](tutorials/03_mlai_mouse_ar.ipynb) | The Mathis lab's real pipeline on the shared tables: lab layer, automatic ingestion, legacy tables. |

A local database: `make init` once, then `make db_up` (from the repository root).
