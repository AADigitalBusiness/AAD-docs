"""Tests for the package version and the release helper."""
from __future__ import annotations

import importlib.util
import re
import tomllib
from pathlib import Path

import pytest

import aad_docs

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_release_tool():
    spec = importlib.util.spec_from_file_location("release_tool", REPO_ROOT / "tools" / "release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_is_exposed_and_valid() -> None:
    release = _load_release_tool()
    assert aad_docs.__version__ == release.current_version()
    assert release.VERSION_RE.match(aad_docs.__version__)


def test_pyproject_reads_the_version_from_one_place() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" in project["project"]["dynamic"]
    assert "version" not in project["project"]
    assert project["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "aad_docs._version.__version__"}


def test_changelog_keeps_an_unreleased_section() -> None:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## Unreleased$", text, re.MULTILINE)


@pytest.mark.parametrize(
    "older, newer",
    [
        ("0.1.0", "0.1.1"),
        ("0.1.9", "0.2.0"),
        ("0.9.0", "1.0.0"),
        ("0.2.0a1", "0.2.0b1"),
        ("0.2.0b2", "0.2.0rc1"),
        ("0.2.0rc1", "0.2.0"),
    ],
)
def test_release_tool_orders_versions(older: str, newer: str) -> None:
    release = _load_release_tool()
    assert release.sort_key(older) < release.sort_key(newer)


def test_release_tool_closes_the_unreleased_section() -> None:
    release = _load_release_tool()
    changelog = "# Changelog\n\n## Unreleased\n\n- Added a thing.\n\n## 0.1.0 · 2026-01-01\n\n- First.\n"
    result = release.release_notes("0.2.0", "2026-02-02", changelog)
    assert "## Unreleased\n\n## 0.2.0 · 2026-02-02\n\n- Added a thing." in result


def test_release_tool_refuses_an_empty_unreleased_section() -> None:
    release = _load_release_tool()
    with pytest.raises(SystemExit):
        release.release_notes("0.2.0", "2026-02-02", "# Changelog\n\n## Unreleased\n\n## 0.1.0 · 2026-01-01\n\n- First.\n")
