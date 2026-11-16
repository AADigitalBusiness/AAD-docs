"""Routing and URL resolution for AAD-docs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import apps
from django.http import Http404
from django.urls import reverse

from aad_docs.conf import get_settings
from aad_docs.discovery import (
     build_tree,
    parse_doc_filename,
    strip_numeric_prefix,
)
from aad_docs.nodes import Node, Page


def _find_app_node(slug_or_label: str) -> Node | None:
    tree = build_tree()
    for node in tree:
        if node.slug == slug_or_label or node.app_label == slug_or_label:
            return node
    hyphenated = slug_or_label.replace("_", "-")
    for node in tree:
        if node.slug == hyphenated:
            return node
    return None


def _find_model_in_app(app_label: str | None, model_slug: str) -> Any | None:
    if not app_label:
        return None
    try:
        app_config = apps.get_app_config(app_label)
    except LookupError:
        return None
    for model in app_config.get_models():
        if model._meta.model_name == model_slug:
            return model
    return None


def _find_model_folder_page(model_dir: Path, page_slug: str) -> Page | None:
    if not model_dir.is_dir():
        return None
    cfg = get_settings()
    languages: list[str] = list(cfg.get("LANGUAGES") or ["en", "es"])
    default_lang = languages[0] if languages else "en"

    matched_page: Page | None = None
    for entry in sorted(model_dir.iterdir(), key=lambda p: p.name):
        if entry.is_dir() or entry.name.startswith("."):
            continue
        parsed = parse_doc_filename(entry.name, languages)
        if parsed is None:
            continue
        raw_stem, slug, lang, kind = parsed
        if page_slug not in (slug, raw_stem):
            continue
        if matched_page is None:
            matched_page = Page(
                slug=slug,
                title=slug,
                kind=kind,
                languages=[],
                variants={},
                raw_stem=raw_stem,
            )
        if lang not in matched_page.languages:
            matched_page.languages.append(lang)
        matched_page.variants[lang] = str(entry)

    if matched_page is not None:
        matched_page.languages.sort(key=lambda l: (0 if l == default_lang else 1, l))
    return matched_page


def resolve_path(app_slug: str, path: str) -> tuple[str, Any]:
    """Turn the path after the app slug into a section, a model or a page.

    Rejects any path that leaves the node folder. The section wins over a model with the same slug (D007).
    """
    app_node = _find_app_node(app_slug)
    if app_node is None or app_node.path is None:
        raise Http404(f"Unknown documentation node: {app_slug}")

    node_root = app_node.path.resolve()
    raw_path = (path or "").strip("/")
    if not raw_path:
        return ("section", app_node)

    parts = raw_path.split("/")
    for part in parts:
        if not part or part in (".", "..") or part.startswith("."):
            raise Http404("Invalid documentation path")

    candidate_fs = (node_root / raw_path).resolve()
    if not candidate_fs.is_relative_to(node_root):
        raise Http404("Path leaves node directory")

    # 1. Try resolving through sections and pages (section wins over model on collision, D007)
    current = app_node
    for idx, part in enumerate(parts):
        is_last = idx == len(parts) - 1

        # Match child section node first
        matched_child = None
        for child in current.children:
            if part in (child.slug, strip_numeric_prefix(child.raw_name)):
                matched_child = child
                break

        if matched_child is not None:
            if is_last:
                return ("section", matched_child)
            current = matched_child
            continue

        # If this is the last segment, match a page in current node
        if is_last:
            for pg in current.page_items:
                if part == pg.slug or (pg.raw_stem == part and not any(other.slug == part for other in current.page_items)):
                    # Only answer at the clean slug address (or raw_stem when identical to slug)
                    if part == pg.slug:
                        return ("page", (current, pg))
        break

    # 2. Try resolving as a model of the app or a hand-written page inside <app>/docs/<model-slug>/
    model_cls = _find_model_in_app(app_node.app_label, parts[0])
    if model_cls is not None:
        if len(parts) == 1:
            return ("model", (app_node, model_cls))
        if len(parts) == 2:
            model_dir = (node_root / parts[0]).resolve()
            if not model_dir.is_relative_to(node_root):
                raise Http404("Invalid model folder path")
            model_page = _find_model_folder_page(model_dir, parts[1])
            if model_page is not None and parts[1] == model_page.slug:
                return ("page", (app_node, model_page))

    raise Http404(f"Documentation path not found: {app_slug}/{raw_path}")


def docs_url(target: Any, *parts: str) -> str:
    """Return the address of an app, a model or one of their pages."""
    clean_parts = [strip_numeric_prefix(str(p).strip("/")) for p in parts if p]

    # Django Model class or instance
    meta = getattr(target, "_meta", None)
    if meta is not None and hasattr(meta, "app_label") and hasattr(meta, "model_name"):
        app_node = _find_app_node(meta.app_label)
        app_slug = app_node.slug if (app_node and app_node.slug) else meta.app_label.replace("_", "-")
        subpath = "/".join([meta.model_name, *clean_parts])
        return reverse("aad_docs:page", kwargs={"app_slug": app_slug, "path": subpath})

    # Node instance
    if isinstance(target, Node):
        app_slug = target.slug or ""
    else:
        target_str = str(target)
        app_node = _find_app_node(target_str)
        app_slug = app_node.slug if (app_node and app_node.slug) else target_str.replace("_", "-")

    if clean_parts:
        return reverse("aad_docs:page", kwargs={"app_slug": app_slug, "path": "/".join(clean_parts)})
    return reverse("aad_docs:node", kwargs={"app_slug": app_slug})
