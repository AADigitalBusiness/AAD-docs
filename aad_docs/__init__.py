"""AAD-docs package root.

Imports no Django code so a docs/__init__.py can import Node before Django is ready.
"""
from __future__ import annotations

from typing import Any

from aad_docs._version import __version__
from aad_docs.nodes import Node


def docs_url(target: Any, *parts: str) -> str:
    """Return the address of an app, a model or one of their pages."""
    from aad_docs.routing import docs_url as _docs_url

    return _docs_url(target, *parts)


__all__ = ["Node", "__version__", "docs_url"]
