"""The Demo lab's pipeline on SCENE, used by ``03_scene_onboarding_demo.ipynb``.

- ``db``: connect and bind every schema (``connect``)
- ``layout``, ``manifest``: how the lab's data is organised on disk, and read into checked objects
- ``register``, ``ingest``: write it to the shared tables and to the lab's own
- ``schemas``: the lab's own tables, on top of the shared ones
- ``plots``, ``display``: figures and code listings for the notebook
"""
