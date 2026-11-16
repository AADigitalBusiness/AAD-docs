"""
Routing module for AAD-docs.

Handles URL resolution for documentation addresses.
"""

from typing import Any

from django.urls import reverse

from aad_docs.discovery import build_tree


def _get_routing_loaded() -> bool:
    """Check if Django URLs are loaded."""
    try:
        from django.urls import get_resolver
        resolver = get_resolver()
        return resolver is not None
    except Exception:
        return False


def _ensure_routing_loaded() -> None:
    """Ensure Django routing is loaded (called lazily)."""
    if not _get_routing_loaded():
        from django.core.urlresolvers import clear_url_caches
        from django.conf import settings as django_settings
        
        if hasattr(django_settings, "ROOT_URLCONF"):
            # Force URL loading
            from django.urls import get_resolver
            get_resolver()


def resolve_path(app_slug: str, path: str) -> tuple[str, Any]:
    """
    Turn the path after the app slug into a section, model, or page.
    
    Args:
        app_slug: The app slug from the URL
        path: The remaining path components
    
    Returns:
        Tuple of (resolved_type, target) where resolved_type is one of:
        - "section": target is a Node
        - "model": target is a model class
        - "page": target is a Node and page_name
    
    Raises:
        Http404 if path leaves the node folder or is invalid.
    """
    from django.http import Http404
    
    tree = build_tree()
    
    # Find the app node
    app_node = None
    for child in tree.children:
        if child.slug == app_slug:
            app_node = child
            break
    
    if app_node is None:
        raise Http404(f"No documentation found for app: {app_slug}")
    
    # If no path, return the node itself
    if not path:
        return ("node", app_node)
    
    # Split path into components
    parts = path.strip("/").split("/")
    
    # Check if path tries to leave the node folder
    for part in parts:
        if part.startswith("..") or part in ("..", "."):
            raise Http404("Invalid path")
    
    # Resolve the path
    current = app_node
    resolved_parts = []
    
    for i, part in enumerate(parts):
        # Check if this part matches a child node
        child_node = None
        for child in current.children:
            if child.slug == part:
                child_node = child
                break
        
        if child_node:
            current = child_node
            resolved_parts.append(part)
            continue
        
        # Check if this part matches a page
        if part in [p.slug for p in current.pages] if current.pages else any(
            part == p.stem for p in Path(current_path).glob("*.md")
        ):
            resolved_parts.append(part)
            return ("page", (current, part))
        
        # No match found
        raise Http404(f"No page or section found: {part}")
    
    return ("node", current)


def _get_docs_url_impl(target: Any, page_name: str | None = None) -> str:
    """
    Implementation of docs_url that requires Django routing to be loaded.
    
    This is called lazily from the exported docs_url function.
    """
    from django.urls import reverse
    
    # Handle string (app label)
    if isinstance(target, str):
        if page_name:
            return reverse("aad_docs:page", kwargs={"app_slug": target, "path": page_name})
        return reverse("aad_docs:node", kwargs={"app_slug": target})
    
    # Handle Django model
    try:
        from django.db.models import Model
        if isinstance(target, type) and issubclass(target, Model):
            app_label = target._meta.app_label
            model_name = target._meta.model_name
            if page_name:
                return reverse(
                    "aad_docs:page",
                    kwargs={
                        "app_slug": app_label,
                        "path": f"{model_name}/{page_name}"
                    }
                )
            return reverse(
                "aad_docs:page",
                kwargs={"app_slug": app_label, "path": model_name}
            )
    except (TypeError, AttributeError):
        pass
    
    # Handle Node
    if hasattr(target, "slug"):
        if page_name:
            return reverse(
                "aad_docs:page",
                kwargs={"app_slug": target.slug, "path": page_name}
            )
        return reverse("aad_docs:node", kwargs={"app_slug": target.slug})
    
    # Fallback
    slug = str(target)
    if page_name:
        return reverse("aad_docs:page", kwargs={"app_slug": slug, "path": page_name})
    return reverse("aad_docs:node", kwargs={"app_slug": slug})


def docs_url(target: Any, page_name: str | None = None) -> str:
    """
    Return the documentation URL for an app, model, or page.
    
    This is the public API, called from aad_docs/__init__.py.
    It ensures Django routing is loaded before attempting URL resolution.
    """
    _ensure_routing_loaded()
    return _get_docs_url_impl(target, page_name)
