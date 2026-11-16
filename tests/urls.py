"""URLs for tests."""

from django.urls import include, path

urlpatterns = [
    path("docs/", include("aad_docs.urls")),
]
