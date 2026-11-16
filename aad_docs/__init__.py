"""
AAD-docs: Django app that turns docs/ folders into navigable documentation.

This module exports Node (pure Python, no Django dependencies) and docs_url.
"""

from aad_docs.nodes import Node


def docs_url(target, page_name: str | None = None) -> str:
    """
    Return the documentation URL for an app, model, or page.
    
    Loads routing on first call to avoid AppRegistryNotReady errors.
    
    Args:
        target: An app label string, a Django model class, or a node slug.
        page_name: Optional page name within the target.
    
    Returns:
        The absolute URL path for the documentation.
    """
    # Lazy import to avoid Django imports at module level
    from aad_docs.routing import _get_docs_url_impl
    return _get_docs_url_impl(target, page_name)


__all__ = ["Node", "docs_url"]
