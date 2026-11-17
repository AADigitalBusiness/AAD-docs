"""Take guide screenshots with the browser pattern from django-dsadmin.

Adapted from django-dsadmin commit 47984103f45d3ee6f34005960aa05f946b7f00ae.
See decision 0014.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError, CommandParser

from aad_docs.conf import get_settings
from aad_docs.routing import _find_app_node


class Command(BaseCommand):
    """Retake the screenshots of the guides against a local server in each language."""

    help = "Take guide screenshots in each configured language and save them to assets/*.png."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("app_labels", nargs="*", help="Optional app labels.")
        parser.add_argument(
            "--base-url",
            default="http://127.0.0.1:8000",
            help="Address of the running Django project (default: http://127.0.0.1:8000).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        base_url = options["base_url"].rstrip("/")
        parsed_url = urlsplit(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise CommandError("--base-url must be an http:// or https:// address.")

        cfg = get_settings()
        languages: list[str] = list(cfg.get("LANGUAGES") or ["en", "es"])
        app_labels: list[str] = options.get("app_labels") or ["aad_docs"]
        targets: list[tuple[str, Path]] = []

        for label in app_labels:
            try:
                app_config = apps.get_app_config(label)
            except LookupError as exc:
                raise CommandError(str(exc)) from exc
            guides_dir = Path(app_config.path) / "docs" / "05-guides"
            if not guides_dir.is_dir():
                continue
            app_node = _find_app_node(label)
            app_slug = app_node.slug if app_node and app_node.slug else label.replace("_", "-")
            targets.append((app_slug, Path(app_config.path) / "docs" / "assets"))

        if not targets:
            self.stdout.write(self.style.WARNING("No documentation guides found."))
            return

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise CommandError(
                "Playwright is required: install aad_docs[screenshots], then run "
                "'playwright install chromium'."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for app_slug, assets_dir in targets:
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    for index, lang in enumerate(languages):
                        suffix = "" if index == 0 else f".{lang}"
                        out_file = assets_dir / f"browse-the-docs{suffix}.png"
                        context = browser.new_context(
                            viewport={"width": 1440, "height": 1000},
                            locale=lang,
                            device_scale_factor=1,
                        )
                        try:
                            page = context.new_page()
                            url = f"{base_url}/docs/{app_slug}/guides/browse-the-docs/"
                            response = page.goto(url, wait_until="networkidle")
                            if response is None or not response.ok:
                                status = response.status if response is not None else "no response"
                                raise CommandError(f"Could not capture {url}: HTTP {status}.")
                            if page.url.rstrip("/") != url.rstrip("/"):
                                raise CommandError(
                                    f"Could not capture {url}: redirected to {page.url}. "
                                    "Make the local documentation accessible before taking screenshots."
                                )
                            page.screenshot(path=str(out_file), full_page=True)
                            self.stdout.write(f"Wrote {out_file}")
                        finally:
                            context.close()
            finally:
                browser.close()
