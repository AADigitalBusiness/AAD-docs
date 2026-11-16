"""Views and access control for AAD-docs."""
from __future__ import annotations

from copy import copy
from pathlib import Path
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.views import View

from aad_docs.conf import get_settings
from aad_docs.discovery import build_tree
from aad_docs.language import get_active_language
from aad_docs.nodes import Node, Page
from aad_docs.readers import read_page
from aad_docs.routing import _find_app_node, resolve_path

ALLOWED_ASSET_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _is_item_visible(node: Node, request: HttpRequest, item_name: str, alt_name: str = "") -> bool:
    if not callable(node.visible):
        return True
    if not node.visible(request, item_name):
        return False
    if alt_name and alt_name != item_name and not node.visible(request, alt_name):
        return False
    return True


def _filter_node_for_request(node: Node, request: HttpRequest) -> Node:
    filtered = copy(node)
    filtered.page_items = [
        pg for pg in node.page_items if _is_item_visible(node, request, pg.slug, pg.raw_stem)
    ]
    filtered.children = [
        _filter_node_for_request(ch, request)
        for ch in node.children
        if _is_item_visible(node, request, ch.slug or "", ch.raw_name)
    ]
    return filtered


def _base_context(request: HttpRequest, *, active_app_node: Node | None = None, current_node: Node | None = None) -> dict[str, Any]:
    cfg = get_settings()
    raw_tree = build_tree()
    tree = [_filter_node_for_request(n, request) for n in raw_tree]
    lang = get_active_language(getattr(request, "LANGUAGE_CODE", None))
    return {
        "tree": tree,
        "app_node": _filter_node_for_request(active_app_node, request) if active_app_node else None,
        "node": _filter_node_for_request(current_node, request) if current_node else None,
        "active_language": lang,
        "configured_languages": cfg.get("LANGUAGES", ["en", "es"]),
        "scripts": [],
    }


class DocsAccessMixin:
    """Applies the ACCESS setting to every view."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        cfg = get_settings()
        access = cfg.get("ACCESS", "staff")
        user = getattr(request, "user", None)

        if access == "public":
            allowed = True
        elif access == "authenticated":
            allowed = bool(user and getattr(user, "is_authenticated", False))
        elif access == "staff":
            allowed = bool(user and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False))
        elif callable(access):
            allowed = bool(access(request))
        else:
            allowed = False

        if not allowed:
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]


class IndexView(DocsAccessMixin, View):
    """Shows the root node and the list of app nodes."""

    def get(self, request: HttpRequest) -> HttpResponse:
        ctx = _base_context(request)
        root_node = ctx["tree"][0] if ctx["tree"] else None
        ctx["node"] = root_node
        return render(request, "aad_docs/node.html", ctx)


class NodeView(DocsAccessMixin, View):
    """Shows one node with its pages and children."""

    def get(self, request: HttpRequest, app_slug: str) -> HttpResponse:
        app_node = _find_app_node(app_slug)
        if app_node is None or app_node.slug != app_slug:
            raise Http404(f"Node not found: {app_slug}")
        ctx = _base_context(request, active_app_node=app_node, current_node=app_node)
        return render(request, "aad_docs/node.html", ctx)


class PageView(DocsAccessMixin, View):
    """Shows one page, one section or one model in the active language."""

    def get(self, request: HttpRequest, app_slug: str, path: str) -> HttpResponse:
        app_node = _find_app_node(app_slug)
        if app_node is None or app_node.slug != app_slug:
            raise Http404(f"Node not found: {app_slug}")

        kind, resolved = resolve_path(app_slug, path)
        lang = get_active_language(getattr(request, "LANGUAGE_CODE", None))

        if kind == "section":
            section_node: Node = resolved
            if not _is_item_visible(app_node, request, section_node.slug or "", section_node.raw_name):
                raise Http404("Section is hidden")
            ctx = _base_context(request, active_app_node=app_node, current_node=section_node)
            return render(request, "aad_docs/node.html", ctx)

        if kind == "model":
            owner_node, model_cls = resolved
            from aad_docs.codemap.models import build_model_mermaid_diagram, describe_single_model
            from aad_docs.routing import _find_model_folder_page

            model_info = describe_single_model(model_cls)
            diagram_code = build_model_mermaid_diagram(model_cls._meta.app_label)
            model_dir = (owner_node.path / model_cls._meta.model_name) if owner_node.path else None
            extra_pages: list[Page] = []
            if model_dir and model_dir.is_dir():
                for entry in sorted(model_dir.iterdir(), key=lambda p: p.name):
                    if not entry.is_dir() and not entry.name.startswith("."):
                        pg = _find_model_folder_page(model_dir, entry.stem.split(".")[0])
                        if pg and all(x.slug != pg.slug for x in extra_pages):
                            extra_pages.append(pg)

            ctx = _base_context(request, active_app_node=owner_node, current_node=owner_node)
            ctx["model"] = model_info
            ctx["diagram"] = diagram_code
            ctx["model_pages"] = extra_pages
            ctx["scripts"] = ["aad_docs/vendor/mermaid.min.js"]
            return render(request, "aad_docs/page_model.html", ctx)

        owner_node, page_meta = resolved
        if not _is_item_visible(owner_node, request, page_meta.slug, page_meta.raw_stem):
            raise Http404("Page is hidden")

        try:
            rendered_page = read_page(page_meta, lang_code=lang, node_dir=owner_node.path)
        except (ValueError, FileNotFoundError) as exc:
            raise Http404(str(exc)) from exc

        ctx = _base_context(request, active_app_node=app_node, current_node=owner_node)
        ctx["page"] = rendered_page
        ctx["scripts"] = rendered_page.scripts

        template_map = {
            "md": "aad_docs/page_md.html",
            "mdx": "aad_docs/page_md.html",
            "yml": "aad_docs/page_explorer.html",
            "yaml": "aad_docs/page_explorer.html",
            "csv": "aad_docs/page_table.html",
            "json": "aad_docs/page_simulator.html",
        }
        template_name = template_map.get(rendered_page.kind, "aad_docs/page_md.html")
        return render(request, template_name, ctx)


class AssetView(DocsAccessMixin, View):
    """Serves an image of a closed list of types, SVG excluded, from a node's assets folder."""

    def get(self, request: HttpRequest, app_slug: str, file: str) -> HttpResponse:
        app_node = _find_app_node(app_slug)
        if app_node is None or app_node.slug != app_slug or app_node.path is None:
            raise Http404("Node not found")

        ext = Path(file).suffix.lower()
        if ext not in ALLOWED_ASSET_TYPES:
            raise Http404("Asset type not allowed")

        assets_root = (app_node.path / "assets").resolve()
        target = (assets_root / file).resolve()
        if not target.is_relative_to(assets_root) or not target.is_file():
            raise Http404("Asset not found")

        return HttpResponse(target.read_bytes(), content_type=ALLOWED_ASSET_TYPES[ext])
