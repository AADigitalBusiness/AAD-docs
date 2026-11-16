"""Model metadata introspection for AAD-docs."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings as django_settings


def is_default_model_docstring(model_cls: Any) -> bool:
    """Return True if model_cls has no custom docstring (only Django's generated Model(field, ...))."""
    doc = (getattr(model_cls, "__doc__", None) or "").strip()
    if not doc:
        return True
    return doc.startswith(f"{model_cls.__name__}(")


def clean_model_docstring(model_cls: Any) -> str:
    """Return the cleaned custom docstring of a model, or empty string if none."""
    if is_default_model_docstring(model_cls):
        return ""
    return inspect.cleandoc(model_cls.__doc__ or "").strip()


def _rel_file_for(cls_or_fn: Any) -> str:
    try:
        src = inspect.getsourcefile(cls_or_fn)
        if not src:
            return ""
        p = Path(src).resolve()
        base = getattr(django_settings, "BASE_DIR", None)
        if base:
            root = Path(base).resolve().parent if Path(base).name == "demo" else Path(base).resolve()
            if p.is_relative_to(root):
                return p.relative_to(root).as_posix()
        return p.name
    except Exception:
        return ""


def describe_single_model(model_cls: Any) -> dict[str, Any]:
    """Read _meta, field options and docstring of one Django model."""
    meta = model_cls._meta
    fields_info: list[dict[str, Any]] = []
    relations_info: list[dict[str, str]] = []

    all_fields = list(meta.local_fields) + list(meta.local_many_to_many)
    for f in all_fields:
        internal_type = f.get_internal_type() if hasattr(f, "get_internal_type") else type(f).__name__
        rel_target = ""
        if getattr(f, "is_relation", False) and getattr(f, "related_model", None) is not None:
            rel_model = f.related_model
            if rel_model == "self" or rel_model is model_cls:
                rel_target = f"{meta.app_label}.{meta.object_name}"
            elif hasattr(rel_model, "_meta"):
                rel_target = f"{rel_model._meta.app_label}.{rel_model._meta.object_name}"
            if rel_target:
                relations_info.append(
                    {
                        "field": f.name,
                        "kind": internal_type,
                        "target": rel_target,
                        "target_model_name": getattr(getattr(rel_model, "_meta", None), "model_name", meta.model_name),
                    }
                )

        fields_info.append(
            {
                "name": f.name,
                "type": internal_type,
                "verbose_name": str(getattr(f, "verbose_name", f.name)),
                "help_text": str(getattr(f, "help_text", "") or ""),
                "required": not bool(getattr(f, "blank", False) or getattr(f, "null", False) or getattr(f, "primary_key", False)),
                "primary_key": bool(getattr(f, "primary_key", False)),
                "relation": rel_target,
            }
        )

    return {
        "name": meta.object_name,
        "model_name": meta.model_name,
        "app_label": meta.app_label,
        "verbose_name": str(meta.verbose_name),
        "verbose_name_plural": str(meta.verbose_name_plural),
        "docstring": clean_model_docstring(model_cls),
        "file": _rel_file_for(model_cls),
        "fields": fields_info,
        "relations": relations_info,
    }


def describe_models(app_label: str) -> list[dict[str, Any]]:
    """Read _meta, field options and docstrings of an app's models."""
    try:
        app_config = apps.get_app_config(app_label)
    except LookupError:
        return []
    return [describe_single_model(m) for m in app_config.get_models()]


def build_model_mermaid_diagram(app_label: str) -> str:
    """Build a Mermaid flowchart/class diagram from the models and relations of an app."""
    models_data = describe_models(app_label)
    if not models_data:
        return "flowchart LR\n    empty[\"No models\"]"

    lines = ["flowchart LR"]
    for m in models_data:
        lines.append(f'    {m["model_name"]}["{m["name"]}"]')
    for m in models_data:
        for rel in m["relations"]:
            tgt = rel["target_model_name"]
            label = rel["field"]
            lines.append(f'    {m["model_name"]} -->|"{label}"| {tgt}')
    return "\n".join(lines)
