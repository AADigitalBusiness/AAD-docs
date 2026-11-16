"""URL patterns under the aad_docs namespace."""
from __future__ import annotations

from django.urls import path

from aad_docs import views

app_name = "aad_docs"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("<slug:app_slug>/", views.NodeView.as_view(), name="node"),
    path("<slug:app_slug>/assets/<path:file>", views.AssetView.as_view(), name="asset"),
    path("<slug:app_slug>/<path:path>/", views.PageView.as_view(), name="page"),
]
