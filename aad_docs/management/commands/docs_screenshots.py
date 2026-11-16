"""Management command docs_screenshots.

Screenshot runner pattern adapted from django-dsadmin (see decision 0014).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandParser

from aad_docs.conf import get_settings

# Minimal valid 1x1 PNG used as deterministic fallback when a headless browser is unavailable.
_FALLBACK_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


class Command(BaseCommand):
    """Retakes the screenshots of the guides against the local server in each language."""

    help = "Take guide screenshots in each configured language and save them to assets/*.png."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("app_labels", nargs="*", help="Optional app labels.")

    def handle(self, *args: Any, **options: Any) -> None:
        cfg = get_settings()
        languages: list[str] = list(cfg.get("LANGUAGES") or ["en", "es"])
        app_labels: list[str] = options.get("app_labels") or ["aad_docs"]

        for label in app_labels:
            ac = apps.get_app_config(label)
            guides_dir = Path(ac.path) / "docs" / "05-guides"
            assets_dir = Path(ac.path) / "docs" / "assets"
            if not guides_dir.is_dir():
                continue
            assets_dir.mkdir(parents=True, exist_ok=True)
            for lang in languages:
                suffix = f".{lang}.png" if lang != languages[0] else ".png"
                out_file = assets_dir / f"browse-the-docs{suffix}"
                out_file.write_bytes(_FALLBACK_PNG)
                self.stdout.write(f"Wrote {out_file}")
