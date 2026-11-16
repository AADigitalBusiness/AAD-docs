"""URL resolver introspection for AAD-docs."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings as django_settings
from django.urls import URLPattern, URLResolver, get_resolver


def _rel_path(file_path: str | None, app_path: Path | None = None) -> str:
    if not file_path:
        return ""
    p = Path(file_path).resolve()
    if app_path is not None and p.is_relative_to(app_path.parent):
        return p.relative_to(app_path.parent).as_posix()
    base = getattr(django_settings, "BASE_DIR", None)
    if base:
        root = Path(base).resolve().parent if Path(base).name == "demo" else Path(base).resolve()
        if p.is_relative_to(root):
            return p.relative_to(root).as_posix()
    return p.name


def _unwrap_callback(callback: Any) -> tuple[str, str]:
    view_cls = getattr(callback, "view_class", None)
    target = view_cls if view_cls is not None else callback
    name = getattr(target, "__name__", str(target))
    try:
        src = inspect.getsourcefile(target)
    except TypeError:
        src = None
    return name, (src or "")


def _walk_patterns(
    patterns: list[Any],
    prefix: str = "/",
    namespace: str = "",
) -> list[dict[str, str]]:
    collected: list[dict[str, str]] = []
    for entry in patterns:
        raw_pat = str(entry.pattern)
        joined = ("/" + (prefix.lstrip("/") + raw_pat).lstrip("/")).replace("//", "/")
        if isinstance(entry, URLResolver):
            ns = entry.namespace or namespace
            collected.extend(_walk_patterns(entry.url_patterns, joined, ns))
        elif isinstance(entry, URLPattern):
            view_name, src_file = _unwrap_callback(entry.callback)
            route_name = f"{namespace}:{entry.name}" if (namespace and entry.name) else (entry.name or "")
            collected.append(
                {
                    "path": joined,
                    "name": route_name,
                    "view": view_name,
                    "src_file": src_file,
                }
            )
    return collected


def describe_routes(app_label: str) -> list[dict[str, Any]]:
    """Read the URL resolver and map each route belonging to app_label to its view and file."""
    try:
        app_config = apps.get_app_config(app_label)
        app_path = Path(app_config.path).resolve()
    except LookupError:
        return []

    resolver = get_resolver()
    all_routes = _walk_patterns(resolver.url_patterns)
    app_routes: list[dict[str, Any]] = []

    for r in all_routes:
        src = r["src_file"]
        if not src:
            continue
        src_path = Path(src).resolve()
        if src_path.is_relative_to(app_path):
            item: dict[str, Any] = {
                "path": r["path"],
                "name": r["name"],
                "view": r["view"],
                "file": _rel_path(src, app_path),
            }
            app_routes.append(item)

    return app_routes
