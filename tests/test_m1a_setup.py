"""Tests for milestone M1a: Package, demo and tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from django.core.management import call_command
from django.test import override_settings

from aad_docs.apps import AadDocsConfig
from aad_docs.conf import DEFAULTS, get_settings

REPO_ROOT = Path(__file__).resolve().parent.parent


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
