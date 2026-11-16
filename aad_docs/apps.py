"""App configuration and Django system checks for AAD-docs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import AppConfig
from django.core.checks import Error, register


class AadDocsConfig(AppConfig):
    """Registers the app and its Django system checks."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "aad_docs"
    label = "aad_docs"
    verbose_name = "AAD-docs"

    def ready(self) -> None:
        # System checks are registered at module import time below.
        pass


@register()
def check_aad_docs_packaged_docs(app_configs: Any, **kwargs: Any) -> list[Error]:
    """Verify that the packaged aad_docs/docs/ folder and __init__.py exist."""
    errors: list[Error] = []
    pkg_docs = Path(__file__).resolve().parent / "docs"
    if not (pkg_docs / "__init__.py").is_file():
        errors.append(
            Error(
                "Packaged documentation folder aad_docs/docs/__init__.py is missing.",
                hint="Check package-data in pyproject.toml.",
                id="aad_docs.E001",
            )
        )
    return errors
