"""Show the source of a function in the notebook."""

from __future__ import annotations

import inspect

from IPython.display import Markdown


def display_code(func) -> Markdown:
    """The source of ``func``, as a Python code block."""
    return Markdown(f"```python\n{inspect.getsource(func)}\n```")
