"""Copy the tutorial notebooks from examples/ into the site at build time (mkdocs-gen-files).

Links from a notebook to a docs page (``../../docs/introduction.md``) or to another notebook
(``03_mlai_mouse_ar.ipynb``) are rewritten to the page's URL, because mkdocs-jupyter does not
resolve Markdown links.
"""

import re
from pathlib import Path

import mkdocs_gen_files

_DOCS_LINK = re.compile(r"\]\(\.\./\.\./docs/([\w/-]+)\.md(#[\w-]+)?\)")
_NOTEBOOK_LINK = re.compile(r"\]\(([\w-]+)\.ipynb\)")

for path in sorted(Path("examples/tutorials").glob("*.ipynb")):
    name = f"tutorials/{path.name}"
    text = _DOCS_LINK.sub(r"](../../\1/\2)", path.read_text(encoding="utf-8"))
    text = _NOTEBOOK_LINK.sub(r"](../\1/)", text)
    with mkdocs_gen_files.open(name, "w", encoding="utf-8") as f:
        f.write(text)
    mkdocs_gen_files.set_edit_path(name, f"../{path.as_posix()}")
