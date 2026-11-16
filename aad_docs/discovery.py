"""Discovery and node tree construction for AAD-docs."""
from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from copy import copy
from pathlib import Path
from typing import Any

from django.apps import apps

from aad_docs.conf import get_settings
from aad_docs.nodes import Node, Page

READABLE_EXTENSIONS = (".md", ".mdx", ".yml", ".csv", ".json")
_NUMERIC_PREFIX_RE = re.compile(r"^\d+-")

# Tracks __init__.py import or validation errors for docs_check (D003).
NODE_IMPORT_ERRORS: dict[str, str] = {}

_TREE_CACHE: list[Node] | None = None


def clear_tree_cache() -> None:
    """Clear the cached node tree."""
    global _TREE_CACHE
    _TREE_CACHE = None


def strip_numeric_prefix(name: str) -> str:
    """Remove leading numeric prefix like '01-' from a stem or folder name."""
    return _NUMERIC_PREFIX_RE.sub("", name)


def _human_title(stem_or_folder: str) -> str:
    cleaned = strip_numeric_prefix(stem_or_folder)
    return cleaned.replace("-", " ").replace("_", " ").capitalize()


def parse_doc_filename(filename: str, configured_languages: list[str]) -> tuple[str, str, str, str] | None:
    """Parse a filename into (raw_stem, slug, lang, ext) or None if unreadable."""
    if filename.startswith(".") or filename == "__init__.py":
        return None
    lower = filename.lower()
    matched_ext = None
    for ext in READABLE_EXTENSIONS:
        if lower.endswith(ext):
            matched_ext = ext
            break
    if matched_ext is None:
        return None

    default_lang = configured_languages[0] if configured_languages else "en"
    base = filename[: -len(matched_ext)]
    lang = default_lang

    if "." in base:
        stem_part, maybe_lang = base.rsplit(".", 1)
        if maybe_lang in configured_languages or (len(maybe_lang) == 2 and maybe_lang.isalpha()):
            base = stem_part
            lang = maybe_lang

    raw_stem = base
    slug = strip_numeric_prefix(raw_stem)
    return raw_stem, slug, lang, matched_ext.lstrip(".")


def find_doc_dirs() -> list[Path]:
    """Walk INSTALLED_APPS and the root folder and return each docs/ that has an __init__.py."""
    cfg = get_settings()
    exclude_apps = set(cfg.get("EXCLUDE_APPS") or [])
    result: list[Path] = []
    seen: set[Path] = set()

    root_dir = cfg.get("ROOT")
    if root_dir:
        root_path = Path(root_dir).resolve()
        if (root_path / "__init__.py").is_file():
            result.append(root_path)
            seen.add(root_path)

    for app_config in apps.get_app_configs():
        if app_config.label in exclude_apps:
            continue
        doc_path = (Path(app_config.path) / "docs").resolve()
        if doc_path not in seen and (doc_path / "__init__.py").is_file():
            result.append(doc_path)
            seen.add(doc_path)

    return result


def _load_node_from_init(init_path: Path) -> tuple[Node | None, str | None]:
    """Load __init__.py by file path under a unique module name."""
    digest = hashlib.sha256(str(init_path.resolve()).encode("utf-8")).hexdigest()[:16]
    module_name = f"aad_docs._nodes.m_{digest}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(init_path))
        if spec is None or spec.loader is None:
            return None, f"Could not create module spec for {init_path}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)

        if not hasattr(module, "node"):
            # Empty __init__.py produces a default Node at runtime; recorded as missing 'node' for D003 if needed.
            return Node(), None
        raw_node = getattr(module, "node")
        if not isinstance(raw_node, Node):
            return None, f"'node' in {init_path} is not a Node instance"
        cloned = copy(raw_node)
        cloned.children = []
        cloned.page_items = []
        return cloned, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _extract_quick_title(file_path: Path, fallback: str) -> str:
    """Extract the first Markdown heading without full rendering, or fallback for data files."""
    if file_path.suffix.lower() not in (".md", ".mdx"):
        return fallback
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError:
        return fallback
    if raw.startswith("---\n"):
        end_idx = raw.find("\n---\n", 4)
        if end_idx != -1:
            raw = raw[end_idx + 5 :]
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback


def resolve_node(
    doc_path: Path,
    *,
    app_config: Any = None,
    is_parent_app: bool = False,
) -> Node | None:
    """Load a docs package by file path, read its node attribute, apply defaults, and populate pages/children."""
    doc_path = doc_path.resolve()
    init_path = doc_path / "__init__.py"
    if not init_path.is_file():
        return None

    node, err = _load_node_from_init(init_path)
    if err is not None or node is None:
        NODE_IMPORT_ERRORS[str(doc_path)] = err or "Unknown error"
        return None
    NODE_IMPORT_ERRORS.pop(str(doc_path), None)

    cfg = get_settings()
    languages: list[str] = list(cfg.get("LANGUAGES") or ["en", "es"])
    default_lang = languages[0] if languages else "en"

    node.path = doc_path
    node.raw_name = doc_path.name
    if app_config is not None:
        node.app_label = app_config.label
        if not node.slug:
            node.slug = app_config.label.replace("_", "-")
        if not node.title:
            node.title = str(app_config.verbose_name)
    else:
        if not node.slug:
            folder_name = doc_path.parent.name if is_parent_app else strip_numeric_prefix(doc_path.name)
            node.slug = folder_name.replace("_", "-")
        if not node.title:
            node.title = _human_title(doc_path.name)

    if not node.title_es:
        node.title_es = node.title

    # Discover pages in doc_path (grouping language variants under one Page)
    pages_by_key: dict[tuple[str, str], Page] = {}
    for entry in sorted(doc_path.iterdir(), key=lambda p: p.name):
        if entry.name.startswith(".") or entry.name == "assets" or entry.is_dir():
            continue
        parsed = parse_doc_filename(entry.name, languages)
        if parsed is None:
            continue
        raw_stem, slug, lang, kind = parsed
        key = (raw_stem, kind)
        if key not in pages_by_key:
            pages_by_key[key] = Page(
                slug=slug,
                title=slug,
                kind=kind,
                languages=[],
                variants={},
                raw_stem=raw_stem,
            )
        pg = pages_by_key[key]
        if lang not in pg.languages:
            pg.languages.append(lang)
        pg.variants[lang] = str(entry)

    for pg in pages_by_key.values():
        # Order languages with default_lang first
        pg.languages.sort(key=lambda l: (0 if l == default_lang else 1, l))
        primary_path = pg.variants.get(default_lang) or next(iter(pg.variants.values()))
        pg.title = _extract_quick_title(Path(primary_path), pg.slug)

    # Discover child nodes (subfolders with __init__.py)
    child_nodes: list[Node] = []
    for entry in sorted(doc_path.iterdir(), key=lambda p: p.name):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name == "assets":
            continue
        if (entry / "__init__.py").is_file():
            child = resolve_node(entry, app_config=None, is_parent_app=False)
            if child is not None:
                child.app_label = node.app_label
                child_nodes.append(child)

    child_nodes.sort(key=lambda c: (c.order, c.slug or ""))

    # Apply `pages` ordering and hiding semantics
    if node.pages is not None:
        ordered_pages: list[Page] = []
        ordered_children: list[Node] = []
        for item_name in node.pages:
            matched_page = None
            for pg in pages_by_key.values():
                if item_name in (pg.raw_stem, pg.slug):
                    matched_page = pg
                    break
            if matched_page is not None and matched_page not in ordered_pages:
                ordered_pages.append(matched_page)
                continue
            for ch in child_nodes:
                if item_name in (ch.raw_name, ch.slug) and ch not in ordered_children:
                    ordered_children.append(ch)
                    break
        node.page_items = ordered_pages
        node.children = ordered_children
    else:
        node.page_items = sorted(pages_by_key.values(), key=lambda p: p.raw_stem)
        node.children = child_nodes

    return node


def build_tree(force: bool = False) -> list[Node]:
    """Build and cache the full node tree (list of top-level nodes ordered by (order, slug))."""
    global _TREE_CACHE
    cfg = get_settings()
    use_cache = bool(cfg.get("CACHE_TREE"))
    if use_cache and not force and _TREE_CACHE is not None:
        return _TREE_CACHE

    exclude_apps = set(cfg.get("EXCLUDE_APPS") or [])
    nodes: list[Node] = []
    seen_paths: set[Path] = set()

    root_dir = cfg.get("ROOT")
    if root_dir:
        root_path = Path(root_dir).resolve()
        if (root_path / "__init__.py").is_file():
            root_node = resolve_node(root_path, app_config=None, is_parent_app=False)
            if root_node is not None:
                nodes.append(root_node)
                seen_paths.add(root_path)

    for app_config in apps.get_app_configs():
        if app_config.label in exclude_apps:
            continue
        doc_path = (Path(app_config.path) / "docs").resolve()
        if doc_path not in seen_paths and (doc_path / "__init__.py").is_file():
            app_node = resolve_node(doc_path, app_config=app_config, is_parent_app=True)
            if app_node is not None:
                nodes.append(app_node)
                seen_paths.add(doc_path)

    nodes.sort(key=lambda n: (n.order, n.slug or ""))
    if use_cache:
        _TREE_CACHE = nodes
    return nodes
