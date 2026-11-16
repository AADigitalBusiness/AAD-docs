"""
URL patterns for AAD-docs.

Mount these at /docs/ in the project's urls.py.
"""

from django.urls import path

from aad_docs import views


app_name = "aad_docs"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("<slug:app_slug>/", views.NodeView.as_view(), name="node"),
    path("<slug:app_slug>/<path:path>/", views.PageView.as_view(), name="page"),
    path("<slug:app_slug>/assets/<path:file_path>/", views.AssetView.as_view(), name="asset"),
]
