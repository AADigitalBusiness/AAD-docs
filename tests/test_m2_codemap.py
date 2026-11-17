"""Tests for milestone M2: Code map and model pages."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command
from django.test import Client, override_settings
from django.utils import translation

from aad_docs import docs_url
from aad_docs.codemap.models import build_model_mermaid_diagram
from aad_docs.codemap.writer import write_codemap
from aad_docs.generated import GeneratedManifest, HandEditedError
from demo.catalog.models import Category, Product


@override_settings(AAD_DOCS={"ROOT": Path(__file__).resolve().parent.parent / "docs", "ACCESS": "public"})
def test_model_pages_addresses_and_spanish_translations(client: Client) -> None:
    """Models of demo/catalog have pages at /docs/catalog/<model-slug>/, docs_url(Model) returns it, and Spanish translations work."""
    assert docs_url(Product) == "/docs/catalog/product/"
    assert docs_url(Category) == "/docs/catalog/category/"
    assert docs_url(Product, "lifecycle") == "/docs/catalog/product/lifecycle/"

    res_prod = client.get("/docs/catalog/product/")
    assert res_prod.status_code == 200
    html_en = res_prod.content.decode("utf-8")
    assert "Item offered for sale in the catalog." in html_en
    assert "Unique stock keeping unit code for inventory tracking." in html_en

    # Hand-written file in demo/catalog/docs/product/lifecycle.md shows under the model address
    res_life = client.get("/docs/catalog/product/lifecycle/")
    assert res_life.status_code == 200
    assert "Product lifecycle" in res_life.content.decode("utf-8")

    # Model diagram of demo/catalog is drawn from its relations
    diagram = build_model_mermaid_diagram("catalog")
    assert 'product -->|\"category\"| category' in diagram
    assert 'category -->|\"parent\"| category' in diagram

    # Spanish active: model verbose_name and help_text come from demo/catalog translations
    with translation.override("es"):
        res_es = client.get("/docs/catalog/product/", HTTP_ACCEPT_LANGUAGE="es")
        assert res_es.status_code == 200
        html_es = res_es.content.decode("utf-8")
        assert "Producto" in html_es
        assert "Código único de referencia para el control de inventario." in html_es


def test_generated_manifest_hand_edit_guard_and_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """docs_codemap writes code-map.yml, refuses to overwrite hand edits, and --check detects drift without touching request-flow.json."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "__init__.py").write_text("from aad_docs import Node\nnode = Node(slug='catalog')\n", encoding="utf-8")
    # Pre-existing initial design target code-map.yml and hand-written request-flow.json
    (docs_dir / "code-map.yml").write_text("# Design target\napp: catalog\nstatus: planned\n", encoding="utf-8")
    flow_content = '{"type": "flow", "title": "Untouched", "steps": []}\n'
    (docs_dir / "request-flow.json").write_text(flow_content, encoding="utf-8")

    from django.apps import apps

    catalog_cfg = apps.get_app_config("catalog")
    monkeypatch.setattr(catalog_cfg, "path", str(tmp_path))

    # First run replaces the design target once and writes .generated.yml
    written = write_codemap(["catalog"], include_reference_tables=True)
    assert any(p.endswith("code-map.yml") for p in written)
    assert (docs_dir / ".generated.yml").is_file()
    assert (docs_dir / "request-flow.json").read_text(encoding="utf-8") == flow_content

    # --check passes when up to date
    call_command("docs_codemap", "catalog", check=True)

    # Simulate code change (file on disk is outdated relative to generator, but hash still matches manifest)
    manifest = GeneratedManifest(docs_dir)
    old_text = "app: catalog\nstatus: outdated\n"
    (docs_dir / "code-map.yml").write_text(old_text, encoding="utf-8")
    from aad_docs.generated import sha256_text

    manifest.entries["code-map.yml"] = sha256_text(old_text)
    manifest.save()

    with pytest.raises(CommandError, match="out of date"):
        call_command("docs_codemap", "catalog", check=True)

    # Simulate hand edit (hash on disk differs from .generated.yml)
    (docs_dir / "code-map.yml").write_text("edited by hand\n", encoding="utf-8")
    with pytest.raises(HandEditedError, match="edited by hand"):
        write_codemap(["catalog"])
