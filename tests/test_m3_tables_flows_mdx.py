"""Tests for milestone M3: Tables, flows, .mdx and visual components."""
from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client, override_settings

from aad_docs.codemap.writer import (
    build_model_field_tables,
    build_reference_tables_for_aad_docs,
)
from aad_docs.readers import read_page

REPO_ROOT = Path(__file__).resolve().parent.parent


@override_settings(AAD_DOCS={"ROOT": REPO_ROOT / "docs", "ACCESS": "public"})
def test_reference_tables_and_request_flow_and_embed_mdx(client: Client) -> None:
    """Every file in 06-reference/ opens as a table, request-flow.json plays step by step, and embed-a-piece.mdx mounts pieces while keeping code blocks as text."""
    for name in ("settings", "node-options", "commands", "checks", "file-types", "mdx-tags"):
        res = client.get(f"/docs/aad-docs/reference/{name}/")
        assert res.status_code == 200
        assert b'data-component="table"' in res.content

    res_flow = client.get("/docs/aad-docs/request-flow/")
    assert res_flow.status_code == 200
    assert b'data-component="flow"' in res_flow.content
    assert b"The URL is matched" in res_flow.content
    assert b"aad_docs:page matches the node slug" in res_flow.content
    assert b"aad_docs/urls.py" in res_flow.content

    res_mdx = client.get("/docs/aad-docs/guides/embed-a-piece/")
    assert res_mdx.status_code == 200
    html = res_mdx.content.decode("utf-8")
    # Example tags inside fenced code blocks stay escaped as text
    assert "&lt;Flow src=&quot;order-states.json&quot; /&gt;" in html
    assert "&lt;Model name=&quot;orders.Order&quot; /&gt;" in html
    assert "&lt;Callout type=&quot;warning&quot;&gt;" in html


def test_mdx_mounts_live_components_and_pieces(tmp_path: Path) -> None:
    """An .mdx page with live Table, Flow, Model, Callout, Steps, Tabs, Cards and details renders each component and requests only needed scripts."""
    (tmp_path / "items.csv").write_text("col1,col2\nval1,val2\n", encoding="utf-8")
    (tmp_path / "flow.json").write_text(
        '{"type": "flow", "title": "Order flow", "steps": '
        '[{"title": "Order submitted", "detail": "The user submits the order.", "file": "orders/views.py"}]}',
        encoding="utf-8",
    )
    mdx_file = tmp_path / "live.mdx"
    mdx_file.write_text(
        "# Live MDX\n\nPurpose.\n\n"
        "<Callout type=\"warning\">\nWatch out.\n</Callout>\n\n"
        "<Steps>\n1. First\n2. Second\n</Steps>\n\n"
        "<Tabs>\n<Tab title=\"One\">\nTab 1\n</Tab>\n<Tab title=\"Two\">\nTab 2\n</Tab>\n</Tabs>\n\n"
        "<Cards>\n<Card title=\"Card 1\" href=\"/docs/\">\nBody 1\n</Card>\n</Cards>\n\n"
        "<details open>\n<summary>Summary line</summary>\nDetails body.\n</details>\n\n"
        "<Table src=\"items.csv\" />\n\n"
        "<Flow src=\"flow.json\" />\n\n"
        "<Model name=\"catalog.Product\" />\n",
        encoding="utf-8",
    )
    pg = read_page(mdx_file, node_dir=tmp_path)
    assert 'data-component="callout"' in pg.content
    assert 'data-component="steps"' in pg.content
    assert 'data-component="tabs"' in pg.content
    assert 'data-component="cards"' in pg.content
    assert 'data-component="details"' in pg.content
    assert 'data-component="table"' in pg.content
    assert 'data-component="flow"' in pg.content
    assert 'data-component="model"' in pg.content
    assert set(pg.scripts) == {"aad_docs/tabs.js", "aad_docs/table.js", "aad_docs/simulator.js"}


def test_generated_reference_tables_have_no_milestone_column() -> None:
    """Generated reference tables come from their Python owners and no longer carry the milestone column."""
    tables = build_reference_tables_for_aad_docs()
    assert set(tables.keys()) == {
        "06-reference/settings.csv",
        "06-reference/node-options.csv",
        "06-reference/mdx-tags.csv",
        "06-reference/file-types.csv",
        "06-reference/commands.csv",
        "06-reference/checks.csv",
    }
    for name, csv_text in tables.items():
        header = csv_text.splitlines()[0].split(",")
        assert "milestone" not in header, f"{name} still has milestone column"

    model_tables = build_model_field_tables("catalog")
    assert "06-reference/product-fields.csv" in model_tables
    assert "Unique stock keeping unit code for inventory tracking." in model_tables["06-reference/product-fields.csv"]


def test_mdx_src_path_traversal_and_raw_html_safety(tmp_path: Path) -> None:
    """A tag with a src that leaves the node folder raises ValueError; <details> works in .md while <script> stays escaped as text."""
    bad_mdx = tmp_path / "escape.mdx"
    bad_mdx.write_text("# Escape\n\nPurpose.\n\n<Table src=\"../secret.csv\" />\n", encoding="utf-8")
    with pytest.raises(ValueError, match="leaves the node folder"):
        read_page(bad_mdx, node_dir=tmp_path)

    md_file = tmp_path / "safe.md"
    md_file.write_text(
        "# Safe\n\nPurpose.\n\n<details open>\n<summary>More</summary>\nInside.\n</details>\n\n<script>alert(1)</script>\n",
        encoding="utf-8",
    )
    pg = read_page(md_file, node_dir=tmp_path)
    assert '<details class="plt-details d-collapse"' in pg.content
    assert "<script>" not in pg.content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in pg.content
