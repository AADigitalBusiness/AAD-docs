"""
Views for AAD-docs.

Handles requests to /docs/ URLs and renders documentation pages.
"""

from django.conf import settings as django_settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from aad_docs.conf import get_settings
from aad_docs.discovery import build_tree
from aad_docs.language import pick_variant
from aad_docs.readers import read_page


class DocsAccessMixin:
    """
    Mixin that applies the ACCESS setting to every view.
    
    By default, documentation is staff-only.
    """
    
    def dispatch(self, request: HttpRequest, *args, **kwargs):
        settings = get_settings()
        access = settings.get("ACCESS", "staff")
        
        if access == "staff":
            if not request.user.is_staff:
                return render(request, "aad_docs/access_denied.html", status=403)
        elif access == "public":
            pass  # Always allow
        elif callable(access):
            if not access(request):
                return render(request, "aad_docs/access_denied.html", status=403)
        
        return super().dispatch(request, *args, **kwargs)


class IndexView(DocsAccessMixin, View):
    """Show the root node and the list of app nodes."""
    
    @method_decorator(cache_page(60 * 15))  # 15 minutes
    @method_decorator(vary_on_cookie)
    def get(self, request: HttpRequest) -> HttpResponse:
        tree = build_tree()
        
        context = {
            "node": tree,
            "show_tree": get_settings().get("SHOW_TREE", True),
            "show_language_switcher": get_settings().get("SHOW_LANGUAGE_SWITCHER", True),
        }
        
        return render(request, "aad_docs/index.html", context)


class NodeView(DocsAccessMixin, View):
    """Show one node with its pages and children."""
    
    @method_decorator(cache_page(60 * 15))
    @method_decorator(vary_on_cookie)
    def get(self, request: HttpRequest, app_slug: str) -> HttpResponse:
        tree = build_tree()
        
        # Find the node
        node = None
        for child in tree.children:
            if child.slug == app_slug:
                node = child
                break
        
        if node is None:
            raise Http404(f"No documentation found for app: {app_slug}")
        
        context = {
            "node": node,
            "parent": tree,
            "show_tree": get_settings().get("SHOW_TREE", True),
            "show_language_switcher": get_settings().get("SHOW_LANGUAGE_SWITCHER", True),
        }
        
        return render(request, "aad_docs/node.html", context)


class PageView(DocsAccessMixin, View):
    """Show one page or model in the active language."""
    
    @method_decorator(cache_page(60 * 15))
    @method_decorator(vary_on_cookie)
    def get(self, request: HttpRequest, app_slug: str, path: str) -> HttpResponse:
        from pathlib import Path
        
        tree = build_tree()
        
        # Find the app node
        app_node = None
        for child in tree.children:
            if child.slug == app_slug:
                app_node = child
                break
        
        if app_node is None:
            raise Http404(f"No documentation found for app: {app_slug}")
        
        # Resolve the path to a file
        # Try to find a matching page in the node's docs directory
        docs_dir = None
        for app_config in django_settings.INSTALLED_APPS:
            if app_config.split(".")[-1] == app_slug:
                try:
                    import importlib
                    mod = importlib.import_module(app_config)
                    if hasattr(mod, "__path__"):
                        docs_dir = Path(mod.__path__[0]) / "docs"
                        break
                except ImportError:
                    continue
        
        if docs_dir is None:
            # Try project-level docs
            from aad_docs.discovery import find_doc_dirs
            for doc_dir in find_doc_dirs():
                if doc_dir.name == app_slug or doc_dir.parent.name == app_slug:
                    docs_dir = doc_dir
                    break
        
        if docs_dir is None:
            raise Http404(f"No docs directory found for app: {app_slug}")
        
        # Try to find the file
        file_path = docs_dir / f"{path}.md"
        if not file_path.exists():
            # Try without .md extension
            file_path = docs_dir / path
            if not file_path.exists():
                # Try all possible extensions
                for ext in [".md", ".mdx", ".yml", ".yaml", ".csv", ".json"]:
                    try_path = docs_dir / f"{path}{ext}"
                    if try_path.exists():
                        file_path = try_path
                        break
        
        if not file_path.exists():
            raise Http404(f"No documentation file found: {path}")
        
        # Read the page
        page = read_page(str(file_path))
        
        # Pick the variant for the active language
        lang_code = request.LANGUAGE_CODE if hasattr(request, "LANGUAGE_CODE") else "en"
        variant_path = pick_variant(page, lang_code)
        
        # If variant is different from requested, re-read
        if variant_path and variant_path != str(file_path):
            page = read_page(variant_path)
        
        context = {
            "node": app_node,
            "page": page,
            "parent": tree,
            "show_tree": get_settings().get("SHOW_TREE", True),
            "show_language_switcher": get_settings().get("SHOW_LANGUAGE_SWITCHER", True),
        }
        
        # Use template based on page kind
        template_name = f"aad_docs/page_{page.kind}.html"
        if page.kind == "md":
            template_name = "aad_docs/page_md.html"
        elif page.kind == "mdx":
            template_name = "aad_docs/page_mdx.html"
        else:
            template_name = "aad_docs/page_default.html"
        
        return render(request, template_name, context)


class AssetView(DocsAccessMixin, View):
    """Serve an image of a closed list of types from a node's assets folder."""
    
    def get(self, request: HttpRequest, app_slug: str, file_path: str) -> HttpResponse:
        settings = get_settings()
        allowed_types = settings.get("ASSET_TYPES", [".png", ".jpg", ".jpeg", ".webp", ".gif"])
        
        # Check file extension
        import os
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in allowed_types:
            raise Http404("Asset type not allowed")
        
        # Check for path traversal
        if ".." in file_path or file_path.startswith("/"):
            raise Http404("Invalid asset path")
        
        # Find the asset in the app's docs/assets folder
        from pathlib import Path
        from django.conf import settings as django_settings
        
        asset_path = None
        for app_config in django_settings.INSTALLED_APPS:
            if app_config.split(".")[-1] == app_slug:
                try:
                    import importlib
                    mod = importlib.import_module(app_config)
                    if hasattr(mod, "__path__"):
                        docs_assets = Path(mod.__path__[0]) / "docs" / "assets" / file_path
                        if docs_assets.exists():
                            asset_path = docs_assets
                            break
                except ImportError:
                    continue
        
        if asset_path is None:
            raise Http404("Asset not found")
        
        # Serve the file
        with open(asset_path, "rb") as f:
            content = f.read()
        
        # Determine content type
        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        content_type = content_types.get(ext, "application/octet-stream")
        
        return HttpResponse(content, content_type=content_type)
