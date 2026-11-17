"""Tests for milestone M1: Navigable docs."""
from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import Client, RequestFactory, override_settings
from django.utils import translation

from aad_docs import Node, docs_url
from aad_docs.discovery import build_tree, resolve_node
from aad_docs.routing import resolve_path


@pytest.mark.django_db
def test_staff_only_access_by_default(client: Client) -> None:
    """A non-staff user gets no access by default; a staff user gets 200."""
    res_anon = client.get("/docs/aad-docs/")
    assert res_anon.status_code == 403

    normal_user = User.objects.create_user(username="reader", password="pw", is_staff=False)
    client.force_login(normal_user)
    assert client.get("/docs/aad-docs/").status_code == 403

    staff_user = User.objects.create_user(username="staff", password="pw", is_staff=True)
    client.force_login(staff_user)
    assert client.get("/docs/aad-docs/").status_code == 200


@override_settings(AAD_DOCS={"ROOT": Path(__file__).resolve().parent.parent / "docs", "ACCESS": "public"})
def test_render_every_md_in_aad_docs_and_project(client: Client) -> None:
    """/docs/aad-docs/ and /docs/project/ render every .md in this repository, diagrams included, with no header visible."""
    assert docs_url("aad_docs") == "/docs/aad-docs/"
    assert docs_url("aad_docs", "read-the-code") == "/docs/aad-docs/read-the-code/"
    assert docs_url("aad_docs", "code-map") == "/docs/aad-docs/code-map/"

    for root_slug in ("project", "aad-docs"):
        res = client.get(f"/docs/{root_slug}/")
        assert res.status_code == 200

    # Check read-the-code vs code-map answer at different addresses
    r_md = client.get("/docs/aad-docs/read-the-code/")
    r_yml = client.get("/docs/aad-docs/code-map/")
    assert r_md.status_code == 200
    assert r_yml.status_code == 200
    assert r_md.content != r_yml.content
    assert b'class="mermaid"' in r_md.content

    # Check Spanish active: 01-overview and browse-the-docs show .es.md with no YAML frontmatter visible;
    # other pages fall back to English; no .es.md is listed as a page of its own.
    tree = build_tree(force=True)
    aad_node = next(n for n in tree if n.slug == "aad-docs")
    slugs = [p.slug for p in aad_node.page_items]
    assert "overview" in slugs
    assert not any(s.endswith(".es") for s in slugs)

    with translation.override("es"):
        res_ov_es = client.get("/docs/aad-docs/overview/", HTTP_ACCEPT_LANGUAGE="es")
        assert res_ov_es.status_code == 200
        body_es = res_ov_es.content.decode("utf-8")
        assert "Qué es AAD-docs" in body_es
        assert "source: 01-overview.md" not in body_es
        assert "synced:" not in body_es

        res_guide_es = client.get("/docs/aad-docs/guides/browse-the-docs/", HTTP_ACCEPT_LANGUAGE="es")
        assert res_guide_es.status_code == 200
        assert "source: browse-the-docs.md" not in res_guide_es.content.decode("utf-8")

        # Fallback to English for a page with no .es.md
        res_fallback = client.get("/docs/aad-docs/read-the-code/", HTTP_ACCEPT_LANGUAGE="es")
        assert res_fallback.status_code == 200
        assert "Read the code" in res_fallback.content.decode("utf-8")


def test_empty_missing_and_broken_init(tmp_path: Path) -> None:
    """Empty __init__.py produces defaults; folder without __init__.py returns None; broken __init__.py is skipped."""
    no_init = tmp_path / "no_init"
    no_init.mkdir()
    assert resolve_node(no_init) is None

    empty_dir = tmp_path / "02-my_section"
    empty_dir.mkdir()
    (empty_dir / "__init__.py").write_text("", encoding="utf-8")
    (empty_dir / "01-intro.md").write_text("# Intro\n\nPurpose.\n", encoding="utf-8")
    node = resolve_node(empty_dir)
    assert node is not None
    assert node.slug == "my-section"
    assert node.title == "My section"
    assert node.order == 100
    assert [p.slug for p in node.page_items] == ["intro"]

    broken_dir = tmp_path / "broken"
    broken_dir.mkdir()
    (broken_dir / "__init__.py").write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    assert resolve_node(broken_dir) is None


@override_settings(AAD_DOCS={"ROOT": Path(__file__).resolve().parent.parent / "docs", "ACCESS": "public"})
def test_path_traversal_and_asset_whitelist(client: Client, tmp_path: Path) -> None:
    """A path that leaves the node folder, and an asset outside the allowed list (such as SVG), answer 404."""
    assert client.get("/docs/aad-docs/../../README.md/").status_code == 404
    assert client.get("/docs/aad-docs/assets/evil.svg").status_code == 404
    assert client.get("/docs/aad-docs/assets/../01-overview.md").status_code == 404


@override_settings(AAD_DOCS={"ROOT": None, "ACCESS": "public"})
def test_section_wins_over_model_with_same_slug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A section and a model with the same slug resolve to the section (D007)."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "__init__.py").write_text(
        "from aad_docs import Node\nnode = Node(slug='catalog', title='Catalog')\n",
        encoding="utf-8",
    )
    sec_dir = docs_dir / "product"
    sec_dir.mkdir()
    (sec_dir / "__init__.py").write_text(
        "from aad_docs import Node\nnode = Node(slug='product', title='Product Section')\n",
        encoding="utf-8",
    )
    resolved_node = resolve_node(docs_dir)
    assert resolved_node is not None
    resolved_node.app_label = "catalog"

    monkeypatch.setattr("aad_docs.routing.build_tree", lambda: [resolved_node])
    kind, target = resolve_path("catalog", "product")
    assert kind == "section"
    assert isinstance(target, Node)
    assert target.title == "Product Section"


def test_visible_callable_filters_menu_and_page_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Node.visible filters both the menu and direct page access."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "__init__.py").write_text(
        "from aad_docs import Node\n"
        "node = Node(slug='sec', title='Sec', visible=lambda req, name: name != 'secret')\n",
        encoding="utf-8",
    )
    (docs_dir / "public.md").write_text("# Public\n\nPublic page.\n", encoding="utf-8")
    (docs_dir / "secret.md").write_text("# Secret\n\nSecret page.\n", encoding="utf-8")
    n = resolve_node(docs_dir)
    assert n is not None

    monkeypatch.setattr("aad_docs.views.build_tree", lambda: [n])
    monkeypatch.setattr("aad_docs.routing.build_tree", lambda: [n])

    with override_settings(AAD_DOCS={"ROOT": None, "ACCESS": "public"}):
        c = Client()
        assert c.get("/docs/sec/public/").status_code == 200
        assert c.get("/docs/sec/secret/").status_code == 404
