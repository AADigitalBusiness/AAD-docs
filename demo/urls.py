"""URL configuration for the AAD-docs demo project."""
from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("docs/", include("aad_docs.urls")),
]
