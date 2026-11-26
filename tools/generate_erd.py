import importlib
import os
import pkgutil
import time
import traceback

import datajoint as dj


def configure_datajoint():
    settings = {
        "database.host": os.environ["DJ_HOST"],
        "database.user": os.environ["DJ_USER"],
        "database.password": os.environ["DJ_PASS"],
        "database.port": int(os.environ.get("DJ_PORT", "3306")),
    }

    # DataJoint config API differs across versions:
    # - older: dj.config.update({...})
    # - newer: item assignment / typed config objects
    if hasattr(dj.config, "update"):
        dj.config.update(settings)
        return

    for key, value in settings.items():
        try:
            dj.config[key] = value
            continue
        except Exception:
            pass

        section, field = key.split(".", 1)
        section_obj = getattr(dj.config, section)
        setattr(section_obj, field, value)


def wait_for_database(max_attempts=30, delay_seconds=2):
    last_error = None
    for _ in range(max_attempts):
        try:
            dj.conn().connect()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise RuntimeError(f"MySQL connection failed: {last_error}")


def generate_erd(output_path="scene_pipelines_erd.png"):
    """Save one diagram of every shared schema (each table module under scene_pipelines.schemas)."""
    import scene_pipelines.schemas
    from scene_pipelines.core import SCENE_REGISTRY

    for module in pkgutil.walk_packages(
        scene_pipelines.schemas.__path__, prefix="scene_pipelines.schemas."
    ):
        importlib.import_module(module.name)
    SCENE_REGISTRY.activate_all()

    diagram = None
    for name, schema in sorted(SCENE_REGISTRY.schemas.items()):
        diagram = dj.Diagram(schema) if diagram is None else diagram + dj.Diagram(schema)
        print(f"schema {name}")
    diagram.save(output_path)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    try:
        configure_datajoint()
        wait_for_database()
        generate_erd()
    except Exception:
        traceback.print_exc()
        raise
