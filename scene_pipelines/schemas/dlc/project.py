"""DeepLabCut projects (DlcProject) and their config.yaml versions (ProjectConfig)."""

import datajoint as dj

from scene_pipelines.core.access_markers import WriteRole, mark_write_role
from scene_pipelines.schemas.dlc._schema import schema
from scene_pipelines.schemas.files.files import File  # noqa: F401  # FK: ProjectConfig -> File
from scene_pipelines.schemas.scene.lab import Lab  # noqa: F401  # FK: DlcProject -> Lab
from scene_pipelines.schemas.scene.project import Project  # noqa: F401  # FK: DlcProject -> Project


@mark_write_role(WriteRole.ACQUISITION)
@schema
class DlcProject(dj.Manual):
    """A DeepLabCut project, by the code its lab gives it; write with ``register_dlc_project``."""

    definition = """
    -> Lab
    dlc_project_id: uuid
    ---
    dlc_project_code: varchar(128)  # unique within the lab
    -> [nullable] Project  # the SCENE project
    unique index (lab_id, dlc_project_code)
    """


@mark_write_role(WriteRole.ACQUISITION)
@schema
class ProjectConfig(dj.Manual):
    """One version of a project's config.yaml; write with ``register_project_config``."""

    definition = """
    -> DlcProject
    -> File  # the config.yaml
    ---
    task: varchar(128)  # config Task
    config_date: varchar(16)  # config date, e.g. Oct30
    multianimal: bool
    identity: bool  # false when unset, and in single-animal projects
    pcutoff: float32  # likelihood threshold
    """

    class Bodypart(dj.Part):
        """A bodypart on each animal, in config order."""

        definition = """
        -> master
        bodypart_index: int16
        ---
        bodypart: varchar(64)
        unique index (lab_id, dlc_project_id, file_sha256, bodypart)
        """

    class UniqueBodypart(dj.Part):
        """A bodypart that occurs once per frame, in config order; multi-animal only."""

        definition = """
        -> master
        unique_bodypart_index: int16
        ---
        unique_bodypart: varchar(64)
        unique index (lab_id, dlc_project_id, file_sha256, unique_bodypart)
        """

    class Individual(dj.Part):
        """An animal name, in config order; multi-animal only."""

        definition = """
        -> master
        individual_index: int16
        ---
        individual: varchar(64)
        unique index (lab_id, dlc_project_id, file_sha256, individual)
        """
