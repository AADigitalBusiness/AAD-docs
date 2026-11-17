"""Tests for milestone M4: docs_check (D001 to D065) and docs_screenshots."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.test import override_settings

from aad_docs.checks import CHECKS, run_checks
from aad_docs.generated import GeneratedManifest


def _valid_md(title: str = "Title", purpose: str = "Read this page for testing.") -> str:
    return f"# {title}\n\n{purpose}\n\n```mermaid\nflowchart LR\n    a --> b\n```\n"


def _make_valid_node(root: Path, pages: list[str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    pages_repr = repr(pages) if pages is not None else "None"
    (root / "__init__.py").write_text(
        f"from aad_docs import Node\nnode = Node(slug='test', title='Test', pages={pages_repr})\n",
        encoding="utf-8",
    )
    return root


def test_every_check_rule_has_a_fixture_that_triggers_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify every rule in CHECKS (D001 to D065) triggers on a fixture built to break it."""
    triggered: set[str] = set()

    # D001: installed app has no docs/ folder
    app_no_docs = tmp_path / "app_d001"
    app_no_docs.mkdir()
    from django.apps import apps

    cat_cfg = apps.get_app_config("catalog")
    monkeypatch.setattr(cat_cfg, "path", str(app_no_docs))
    for f in run_checks(["catalog"]):
        triggered.add(f.code)
    assert "D001" in triggered

    # D002: docs/ or subfolder has no __init__.py
    d002 = _make_valid_node(tmp_path / "d002" / "docs")
    (d002 / "sub_without_init").mkdir()
    for f in run_checks(extra_doc_dirs=[d002]):
        triggered.add(f.code)
    assert "D002" in triggered

    # D003: __init__.py fails to import or declares no valid node
    d003 = tmp_path / "d003" / "docs"
    d003.mkdir(parents=True)
    (d003 / "__init__.py").write_text("node = 'not-a-node'\n", encoding="utf-8")
    for f in run_checks(extra_doc_dirs=[d003]):
        triggered.add(f.code)
    assert "D003" in triggered

    # D004: name in pages matches no file or child node
    d004 = _make_valid_node(tmp_path / "d004" / "docs", pages=["missing-page"])
    for f in run_checks(extra_doc_dirs=[d004]):
        triggered.add(f.code)
    assert "D004" in triggered

    # D005: broken relative link
    d005 = _make_valid_node(tmp_path / "d005" / "docs")
    (d005 / "01-page.md").write_text(_valid_md() + "\nSee [broken](does-not-exist.md).\n", encoding="utf-8")
    for f in run_checks(extra_doc_dirs=[d005]):
        triggered.add(f.code)
    assert "D005" in triggered

    # D006: unsupported file extension outside assets/
    d006 = _make_valid_node(tmp_path / "d006" / "docs")
    (d006 / "stray.txt").write_text("hello", encoding="utf-8")
    for f in run_checks(extra_doc_dirs=[d006]):
        triggered.add(f.code)
    assert "D006" in triggered

    # D007: section and model of the same app produce the same slug
    d007_app = tmp_path / "d007_app"
    d007_docs = _make_valid_node(d007_app / "docs")
    _make_valid_node(d007_docs / "01-product")
    (d007_docs / "01-product" / "__init__.py").write_text(
        "from aad_docs import Node\nnode = Node(slug='product', title='Product section')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cat_cfg, "path", str(d007_app))
    for f in run_checks(["catalog"]):
        triggered.add(f.code)
    assert "D007" in triggered

    # D008: two files in the same folder produce the same slug
    d008 = _make_valid_node(tmp_path / "d008" / "docs")
    (d008 / "01-overview.md").write_text(_valid_md(), encoding="utf-8")
    (d008 / "overview.mdx").write_text("# Overview\n\nPurpose.\n", encoding="utf-8")
    for f in run_checks(extra_doc_dirs=[d008]):
        triggered.add(f.code)
    assert "D008" in triggered

    # D010, D011, D012: Spanish page headers and sync date
    d01x = _make_valid_node(tmp_path / "d01x" / "docs")
    (d01x / "01-overview.md").write_text(_valid_md(), encoding="utf-8")
    (d01x / "01-overview.es.md").write_text(_valid_md("Resumen", "Propósito."), encoding="utf-8")  # D011
    (d01x / "02-other.es.md").write_text(
        "---\nsource: missing.md\nsynced: 2026-01-01\n---\n\n" + _valid_md("Otro", "Propósito."),
        encoding="utf-8",
    )  # D012
    (d01x / "03-stale.md").write_text(_valid_md(), encoding="utf-8")
    (d01x / "03-stale.es.md").write_text(
        "---\nsource: 03-stale.md\nsynced: 2020-01-01\n---\n\n" + _valid_md("Viejo", "Propósito."),
        encoding="utf-8",
    )  # D010
    monkeypatch.setattr("aad_docs.checks._git_last_modified_date", lambda p: "2026-11-15")
    for f in run_checks(extra_doc_dirs=[d01x]):
        triggered.add(f.code)
    assert {"D010", "D011", "D012"} <= triggered

    # D020 & D021: model without docstring and field without help_text
    from demo.catalog.models import Product

    monkeypatch.setattr(Product, "__doc__", "Product(id, sku)")
    sku_field = Product._meta.get_field("sku")
    monkeypatch.setattr(sku_field, "help_text", "")
    for f in run_checks(["catalog"]):
        triggered.add(f.code)
    assert {"D020", "D021"} <= triggered
    monkeypatch.undo()

    # D030 & D031: repeated help_text/docstring and hand-written field table
    d03x_app = tmp_path / "d03x_app"
    d03x_docs = _make_valid_node(d03x_app / "docs")
    (d03x_docs / "01-repeat.md").write_text(
        _valid_md()
        + "\nUnique stock keeping unit code for inventory tracking.\n\n"
        + "| Field | Type | Description |\n|---|---|---|\n| sku | CharField | code |\n| price | DecimalField | price |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cat_cfg, "path", str(d03x_app))
    for f in run_checks(["catalog"]):
        triggered.add(f.code)
    assert {"D030", "D031"} <= triggered

    # D032: duplicate long paragraph across two pages
    d032 = _make_valid_node(tmp_path / "d032" / "docs")
    long_para = (
        "This specific documentation paragraph contains more than twenty distinct words and well over one hundred "
        "and twenty characters so that the duplication detector flags it reliably across two files."
    )
    (d032 / "01-a.md").write_text(_valid_md("Page A") + f"\n{long_para}\n", encoding="utf-8")
    (d032 / "02-b.md").write_text(_valid_md("Page B") + f"\n{long_para}\n", encoding="utf-8")
    for f in run_checks(extra_doc_dirs=[d032]):
        triggered.add(f.code)
    assert "D032" in triggered

    # D040 & D041: generated file edited by hand or out of date
    d04x_app = tmp_path / "d04x_app"
    d04x_docs = _make_valid_node(d04x_app / "docs")
    manifest = GeneratedManifest(d04x_docs)
    manifest.write("code-map.yml", "app: catalog\nstatus: outdated\n")
    monkeypatch.setattr(cat_cfg, "path", str(d04x_app))
    for f in run_checks(["catalog"]):
        triggered.add(f.code)
    assert "D041" in triggered
    (d04x_docs / "code-map.yml").write_text("hand edited\n", encoding="utf-8")
    for f in run_checks(["catalog"]):
        triggered.add(f.code)
    assert "D040" in triggered

    # D050, D051, D052: anatomy and guide screenshot checks
    d05x = _make_valid_node(tmp_path / "d05x" / "docs")
    (d05x / "01-bad-anatomy.md").write_text("# Only Title\n\n## Section immediately\n", encoding="utf-8")
    guides = _make_valid_node(d05x / "05-guides")
    (guides / "01-ui.md").write_text(
        _valid_md("UI Guide") + "\n## Steps\n\n1. Click the submit button on the screen.\n",
        encoding="utf-8",
    )
    for f in run_checks(extra_doc_dirs=[d05x]):
        triggered.add(f.code)
    assert {"D050", "D051", "D052"} <= triggered

    # D060, D061, D062, D063, D064, D065: MDX and HTML tag rules
    d06x = _make_valid_node(tmp_path / "d06x" / "docs")
    (d06x / "01-tags.mdx").write_text(
        "# MDX Test\n\nPurpose line.\n\n"
        "import Foo from './foo'\n\n"
        "<UnknownWidget />\n\n"
        "<Table src=\"missing.csv\" />\n\n"
        "<Callout type=\"invalid\">\n"
        "<Tab title=\"Orphan\">\n"
        "Text with <div>raw html</div>.\n",
        encoding="utf-8",
    )
    for f in run_checks(extra_doc_dirs=[d06x]):
        triggered.add(f.code)
    assert {"D060", "D061", "D062", "D063", "D064", "D065"} <= triggered

    assert triggered == set(CHECKS.keys())


def test_docs_screenshots_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """docs_screenshots opens and writes the guide in both configured languages."""
    app_dir = tmp_path / "app_shots"
    guides_dir = app_dir / "docs" / "05-guides"
    guides_dir.mkdir(parents=True)
    from django.apps import apps

    cat_cfg = apps.get_app_config("catalog")
    monkeypatch.setattr(cat_cfg, "path", str(app_dir))
    visits: list[tuple[str, str]] = []

    class FakePage:
        def __init__(self, locale: str) -> None:
            self.locale = locale
            self.url = ""

        def goto(self, url: str, **kwargs: object) -> SimpleNamespace:
            self.url = url
            visits.append((self.locale, url))
            assert kwargs == {"wait_until": "networkidle"}
            return SimpleNamespace(ok=True, status=200)

        def screenshot(self, *, path: str, full_page: bool) -> None:
            assert full_page is True
            Path(path).write_bytes(b"real browser bytes")

    class FakeContext:
        def __init__(self, locale: str) -> None:
            self.locale = locale

        def new_page(self) -> FakePage:
            return FakePage(self.locale)

        def close(self) -> None:
            pass

    class FakeBrowser:
        def new_context(self, **kwargs: object) -> FakeContext:
            assert kwargs["viewport"] == {"width": 1440, "height": 1000}
            return FakeContext(str(kwargs["locale"]))

        def close(self) -> None:
            pass

    class FakePlaywright:
        chromium = SimpleNamespace(launch=lambda: FakeBrowser())

        def __enter__(self) -> "FakePlaywright":
            return self

        def __exit__(self, *args: object) -> None:
            pass

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        SimpleNamespace(sync_playwright=FakePlaywright),
    )
    call_command("docs_screenshots", "catalog", base_url="http://docs.test:8001/")
    assert (app_dir / "docs" / "assets" / "browse-the-docs.png").is_file()
    assert (app_dir / "docs" / "assets" / "browse-the-docs.es.png").is_file()
    assert visits == [
        ("en", "http://docs.test:8001/docs/catalog/guides/browse-the-docs/"),
        ("es", "http://docs.test:8001/docs/catalog/guides/browse-the-docs/"),
    ]
