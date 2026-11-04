"""Connection helpers for the SCENE pipelines tutorials."""

import os
from pathlib import Path

import datajoint as dj

# None outside a clone of the repository (e.g. on Colab): then there is no .env to read.
REPO_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file()), None
)


def connect(prefix: str = "tutorial_") -> None:
    """Configure the DataJoint connection and the SCENE settings for a tutorial.

    Shell variables win, then the repo ``.env``. The schema prefix is never
    taken from ``.env``, so a tutorial cannot write into dev or production schemas.

    Args:
        prefix: Schema prefix of the tutorial databases; must end with ``_``.
    """
    if not prefix.startswith("tutorial_") or not prefix.endswith("_"):
        raise ValueError("tutorial schema prefix must start with 'tutorial_' and end with '_'")
    env_file = REPO_ROOT / ".env" if REPO_ROOT else None
    for line in env_file.read_text().splitlines() if env_file and env_file.is_file() else []:
        name, sep, value = line.partition("=")
        if sep and not name.strip().startswith("#"):
            os.environ.setdefault(name.strip(), value.strip().strip("'\""))
    os.environ["DJ_SCHEMA_PREFIX"] = prefix
    os.environ["AUTO_ACTIVATE"] = ""  # schemas stay unbound until activate_all()
    os.environ.setdefault("SCENE_DEPLOYMENT_ID", "demo-tutorial")
    os.environ.setdefault("SCENE_DEPLOYMENT_LABEL", "Demo lab, tutorial database")

    port = os.environ.get("DJ_PORT") or os.environ.get("MYSQL_PUBLISH_PORT") or 3306
    password = os.environ.get("DJ_PASS") or os.environ.get("MYSQL_ROOT_PASSWORD", "")
    dj.config["database.host"] = os.environ.get("DJ_HOST", "127.0.0.1")
    dj.config["database.port"] = int(port)
    dj.config["database.user"] = os.environ.get("DJ_USER", "root")
    dj.config["database.password"] = password
    dj.config["database.use_tls"] = False
    print(f"{dj.config['database.host']}:{port}, schemas prefixed {prefix!r}")


def drop_tutorial_schemas(prefix: str = "tutorial_") -> list[str]:
    """Drop every database whose name starts with ``prefix``; restart the kernel afterwards.

    Args:
        prefix: Schema prefix of the tutorial databases.

    Returns:
        The names of the dropped databases.
    """
    if not prefix.startswith("tutorial"):
        raise ValueError(f"refusing to drop schemas with prefix {prefix!r}")
    conn = dj.conn()
    names = [n for (n,) in conn.query("SHOW DATABASES").fetchall() if n.startswith(prefix)]
    conn.query("SET FOREIGN_KEY_CHECKS=0")
    try:
        for name in names:
            conn.query(f"DROP DATABASE `{name}`")
    finally:
        conn.query("SET FOREIGN_KEY_CHECKS=1")
    return names
