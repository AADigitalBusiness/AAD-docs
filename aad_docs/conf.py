"""
Configuration defaults for AAD-docs.

This module is the owner of settings.csv.
"""

from typing import Any


DEFAULTS: dict[str, Any] = {
    # Root documentation folder (default: project's docs/)
    "ROOT": None,
    # Access control: "staff" (default), "public", or callable
    "ACCESS": "staff",
    # Whether to show the node tree in the menu
    "SHOW_TREE": True,
    # Whether to enable the language switcher
    "SHOW_LANGUAGE_SWITCHER": True,
    # Allowed asset file types for serving
    "ASSET_TYPES": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    # Cache timeout for node tree (seconds, None = no cache)
    "CACHE_TIMEOUT": None,
    # Debug mode: rebuild tree on every request
    "DEBUG": False,
}


def get_settings() -> dict[str, Any]:
    """
    Return AAD_DOCS settings merged over defaults.
    
    Reads from django.conf.settings.AAD_DOCS if Django is configured,
    otherwise returns only the defaults.
    """
    from django.conf import settings as django_settings
    
    # Check if Django settings are configured by checking if we can access INSTALLED_APPS
    try:
        # Try to access a setting to see if Django is configured
        _ = django_settings.INSTALLED_APPS
        configured = True
    except Exception:
        configured = False
    
    if configured and hasattr(django_settings, "AAD_DOCS") and django_settings.AAD_DOCS:
        custom = django_settings.AAD_DOCS
        if isinstance(custom, dict):
            return {**DEFAULTS, **custom}
    
    return DEFAULTS.copy()
