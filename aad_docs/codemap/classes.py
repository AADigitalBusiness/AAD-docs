"""Module and class docstring introspection for AAD-docs."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from django.apps import apps

from aad_docs.conf import get_settings


def _first_line(doc: str | None) -> str:
    if not doc:
        return ""
    for line in doc.strip().splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _inspect_py_file(py_path: Path, rel_file: str) -> dict[str, Any] | None:
    try:
        source = py_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_path))
    except Exception:
        return None

    entry: dict[str, Any] = {"file": rel_file}
    mod_doc = _first_line(ast.get_docstring(tree))
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    exports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            exports.append(elt.value)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            bases = [
                (b.id if isinstance(b, ast.Name) else getattr(b, "attr", ""))
                for b in node.bases
            ]
            kind = "class"
            if any("View" in b for b in bases):
                kind = "view"
            elif any("Mixin" in b for b in bases):
                kind = "mixin"
            elif any("AppConfig" in b for b in bases):
                kind = "app config"
            classes.append(
                {
                    "name": node.name,
                    "kind": kind,
                    "does": _first_line(ast.get_docstring(node)),
                }
            )
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            functions.append(
                {
                    "name": node.name,
                    "does": _first_line(ast.get_docstring(node)),
                }
            )

    if exports:
        entry["exports"] = exports
    if mod_doc and not classes and not functions:
        entry["does"] = mod_doc
    if classes:
        entry["classes"] = classes
    if functions:
        entry["functions"] = functions
    return entry


def describe_classes(app_label: str) -> list[dict[str, Any]]:
    """List views, modules and classes under CODEMAP_CLASS_DIRS with their docstrings."""
    try:
        app_config = apps.get_app_config(app_label)
        app_path = Path(app_config.path).resolve()
    except LookupError:
        return []

    cfg = get_settings()
    class_dirs = set(cfg.get("CODEMAP_CLASS_DIRS") or ["services"])
    modules: list[dict[str, Any]] = []

    for py_path in sorted(app_path.rglob("*.py")):
        rel_inside = py_path.relative_to(app_path)
        parts = rel_inside.parts
        if any(p.startswith(".") or p in ("docs", "migrations", "tests", "__pycache__") for p in parts):
            continue
        # Include top-level modules, readers/codemap/management submodules, or configured CODEMAP_CLASS_DIRS
        if len(parts) > 1 and parts[0] not in (class_dirs | {"readers", "codemap", "management"}):
            continue
        rel_file = f"{app_path.name}/{rel_inside.as_posix()}"
        info = _inspect_py_file(py_path, rel_file)
        if info:
            modules.append(info)

    return modules
