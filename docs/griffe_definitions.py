"""Show each DataJoint table's ``definition`` in the API reference (a griffe extension).

A class whose ``definition`` is a string literal gets it appended to its docstring as a code
block; the ``definition`` attribute itself is then left out of the page.
"""

from __future__ import annotations

import ast
import inspect

import griffe


class TableDefinitions(griffe.Extension):
    """Append a table's literal ``definition`` to its class docstring."""

    def on_class_members(self, *, cls: griffe.Class, **kwargs) -> None:
        member = cls.members.get("definition")
        if not isinstance(member, griffe.Attribute) or member.value is None:
            return
        try:
            definition = ast.literal_eval(str(member.value))
        except (ValueError, SyntaxError):
            return  # built at import time, e.g. RowMetaBase.build_definition(...)
        if not isinstance(definition, str):
            return
        block = f"Table definition:\n\n```text\n{inspect.cleandoc(definition)}\n```"
        if cls.docstring is None:
            cls.docstring = griffe.Docstring(block, parent=cls)
        else:
            cls.docstring.value = f"{cls.docstring.value}\n\n{block}"
        del cls.members["definition"]
