"""Tests for milestone M1a: Package, demo and tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, override_settings

from aad_docs.apps import AadDocsConfig
from aad_docs.conf import DEFAULTS, get_settings

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_demo_home_redirects_to_docs(client: Client) -> None:
    assert client.get("/").headers["Location"] == "/docs/"


def test_demo_uses_vendored_plt_design_system(client: Client) -> None:
    html = client.get("/docs/").content.decode("utf-8")
    vendor = REPO_ROOT / "aad_docs/static/aad_docs/vendor/plt-design-system.css"
    provenance = vendor.with_name("plt-design-system.PROVENANCE.txt")

    assert vendor.is_file() and "--plt-color-primary" in vendor.read_text(encoding="utf-8")
    assert provenance.is_file() and "@playlovetoys/design-system" in provenance.read_text(encoding="utf-8")
    assert html.index("aad_docs/vendor/plt-design-system.css") < html.index("aad_docs/docs.css")
    assert 'data-theme="brand"' in html
    assert 'class="plt-docs__nav d-card theme-elevated"' in html
    assert 'class="d-select"' in html


@pytest.mark.django_db
def test_demo_admin_uses_standard_django_admin(client: Client) -> None:
    user = get_user_model().objects.create_superuser(username="admin-test", password="pw")
    client.force_login(user)
    html = client.get("/admin/").content.decode("utf-8")

    assert "Django site admin" in html
    assert "dsadmin/css/themes/admin.css" not in html
    assert 'href="/docs/"' in html


def test_import_node_before_django_setup() -> None:
    """from aad_docs import Node works in a fresh Python process before Django is set up."""
    code = (
        "import sys; "
        "from aad_docs import Node; "
        "assert 'django.apps' not in sys.modules; "
        "n = Node(slug='orders', title='Orders'); "
        "assert n.slug == 'orders' and n.order == 100"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr


def test_app_config_and_system_checks() -> None:
    """Smoke test of AadDocsConfig and Django system checks."""
    assert AadDocsConfig.name == "aad_docs"
    call_command("check")


def test_get_settings_merges_over_defaults() -> None:
    """get_settings() merges settings.AAD_DOCS over DEFAULTS."""
    assert set(DEFAULTS.keys()) == {
        "ROOT",
        "ACCESS",
        "LANGUAGES",
        "EXCLUDE_APPS",
        "CODEMAP_CLASS_DIRS",
        "CACHE_TREE",
    }
    with override_settings(AAD_DOCS={"ACCESS": "public", "EXCLUDE_APPS": ["admin"]}):
        cfg = get_settings()
        assert cfg["ACCESS"] == "public"
        assert cfg["EXCLUDE_APPS"] == ["admin"]
        assert cfg["LANGUAGES"] == ["en", "es"]
