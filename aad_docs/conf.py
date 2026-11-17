"""Configuration defaults and settings accessor for AAD-docs.

Copied and adapted from the settings pattern in django-dsadmin commit
47984103f45d3ee6f34005960aa05f946b7f00ae (see decision 0014).
Owner of settings.csv.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "ROOT": "BASE_DIR / docs",
    "ACCESS": "staff",
    "LANGUAGES": ["en", "es"],
    "EXCLUDE_APPS": [],
    "CODEMAP_CLASS_DIRS": ["services"],
    "CACHE_TREE": "not DEBUG",
}

SETTINGS_SPEC: tuple[dict[str, str], ...] = (
    {
        "key": "ROOT",
        "type": "path",
        "default": "BASE_DIR / docs",
        "meaning": "Folder of the root node: documentation that crosses every app. Set to None to have no root node.",
    },
    {
        "key": "ACCESS",
        "type": "str or callable",
        "default": "staff",
        "meaning": "Who can open /docs/. staff: staff users. authenticated: any signed-in user. public: anyone. A callable receives the request and returns a boolean.",
    },
    {
        "key": "LANGUAGES",
        "type": "list of str",
        "default": "en, es",
        "meaning": "Languages a page can exist in. The first one is the default language: every page exists in it and it is the fallback.",
    },
    {
        "key": "EXCLUDE_APPS",
        "type": "list of str",
        "default": "empty",
        "meaning": "App labels whose docs/ folder is ignored.",
    },
    {
        "key": "CODEMAP_CLASS_DIRS",
        "type": "list of str",
        "default": "services",
        "meaning": "Folders inside an app whose classes docs_codemap lists in addition to models and views.",
    },
    {
        "key": "CACHE_TREE",
        "type": "bool",
        "default": "not DEBUG",
        "meaning": "Build the node tree once per process. When false it is rebuilt on every request.",
    },
)


def get_settings() -> dict[str, Any]:
    """Return the AAD_DOCS setting merged over its defaults."""
    resolved: dict[str, Any] = {
        "ROOT": None,
        "ACCESS": "staff",
        "LANGUAGES": list(DEFAULTS["LANGUAGES"]),
        "EXCLUDE_APPS": list(DEFAULTS["EXCLUDE_APPS"]),
        "CODEMAP_CLASS_DIRS": list(DEFAULTS["CODEMAP_CLASS_DIRS"]),
        "CACHE_TREE": False,
    }
    try:
        from django.conf import settings as django_settings

        if not django_settings.configured:
            return resolved

        base_dir = getattr(django_settings, "BASE_DIR", None)
        if base_dir is not None:
            resolved["ROOT"] = Path(base_dir) / "docs"
        resolved["CACHE_TREE"] = not bool(getattr(django_settings, "DEBUG", False))

        user_cfg = getattr(django_settings, "AAD_DOCS", None)
        if isinstance(user_cfg, dict):
            for k, v in user_cfg.items():
                resolved[k] = v
            if "ROOT" in user_cfg and user_cfg["ROOT"] is not None:
                resolved["ROOT"] = Path(user_cfg["ROOT"])
    except Exception:
        pass

    return resolved
