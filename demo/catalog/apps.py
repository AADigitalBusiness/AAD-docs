"""AppConfig for demo.catalog."""
from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CatalogConfig(AppConfig):
    """Configuration for the demo catalog app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "demo.catalog"
    label = "catalog"
    verbose_name = _("Catalog")
