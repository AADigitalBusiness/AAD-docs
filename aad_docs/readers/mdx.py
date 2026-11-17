"""MDX (.mdx) reader and closed visual component registry for AAD-docs.

Line-component parsing adapted from wagtail-shopify content_store (see decision 0014).
Owner of mdx-tags.csv (see decisions 0011, 0012, 0013).
"""
from __future__ import annotations

import html
import re
import shlex
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from django.apps import apps
from django.template.loader import render_to_string

from aad_docs.discovery import strip_numeric_prefix
from aad_docs.nodes import Page
from aad_docs.readers import csv as csv_reader
from aad_docs.readers import json as json_reader
from aad_docs.readers import yaml as yaml_reader
from aad_docs.readers.markdown import (
    _FENCE_RE,
    extract_title,
    make_markdown_renderer,
    split_frontmatter,
)


MDX_TAGS: dict[str, dict[str, Any]] = {
    "Model": {
        "tag": "Model",
        "form": "line",
        "attributes": "name: app_label.ModelName",
        "required_attrs": ("name",),
        "optional_attrs": (),
        "places_in_the_page": "Field table of the model",
        "reads_from": "Model metadata",
        "js": "none",
        "script": None,
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/model.html",
    },
    "ModelDiagram": {
        "tag": "ModelDiagram",
        "form": "line",
        "attributes": "app: app label",
        "required_attrs": ("app",),
        "optional_attrs": (),
        "places_in_the_page": "Diagram of the models of the app and their relations",
        "reads_from": "Model metadata",
        "js": "required",
        "script": "aad_docs/vendor/mermaid.min.js",
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/model_diagram.html",
    },
    "Table": {
        "tag": "Table",
        "form": "line",
        "attributes": "src: path to a .csv",
        "required_attrs": ("src",),
        "optional_attrs": (),
        "places_in_the_page": "Table that sorts and filters",
        "reads_from": "The .csv file",
        "js": "enhance",
        "script": "aad_docs/table.js",
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/table.html",
    },
    "Explorer": {
        "tag": "Explorer",
        "form": "line",
        "attributes": "src: path to a .yml",
        "required_attrs": ("src",),
        "optional_attrs": (),
        "places_in_the_page": "Click-through view of the code map",
        "reads_from": "The .yml file",
        "js": "required",
        "script": "aad_docs/explorer.js",
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/explorer.html",
    },
    "Flow": {
        "tag": "Flow",
        "form": "line",
        "attributes": "src: path to a .json",
        "required_attrs": ("src",),
        "optional_attrs": (),
        "places_in_the_page": "Step-by-step simulator",
        "reads_from": "The .json file, which must have type flow",
        "js": "required",
        "script": "aad_docs/simulator.js",
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/flow.html",
    },
    "Screenshot": {
        "tag": "Screenshot",
        "form": "line",
        "attributes": "name: file stem in assets/",
        "required_attrs": ("name",),
        "optional_attrs": ("alt",),
        "places_in_the_page": "Screenshot in the active language",
        "reads_from": "assets/",
        "js": "none",
        "script": None,
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/screenshot.html",
    },
    "Callout": {
        "tag": "Callout",
        "form": "container",
        "attributes": "type: note, tip, warning or danger",
        "required_attrs": ("type",),
        "optional_attrs": ("title",),
        "allowed_values": {"type": ("note", "tip", "warning", "danger")},
        "places_in_the_page": "Highlighted box around the text it holds",
        "reads_from": "The Markdown between its tags",
        "js": "none",
        "script": None,
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/callout.html",
    },
    "Steps": {
        "tag": "Steps",
        "form": "container",
        "attributes": "none",
        "required_attrs": (),
        "optional_attrs": (),
        "places_in_the_page": "Numbered list drawn as a sequence of steps",
        "reads_from": "The ordered list between its tags",
        "js": "none",
        "script": None,
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/steps.html",
    },
    "Tabs": {
        "tag": "Tabs",
        "form": "container",
        "attributes": "none",
        "required_attrs": (),
        "optional_attrs": (),
        "places_in_the_page": "Tabs, one for each Tab it holds",
        "reads_from": "Its Tab tags",
        "js": "enhance",
        "script": "aad_docs/tabs.js",
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/tabs.html",
    },
    "Tab": {
        "tag": "Tab",
        "form": "container",
        "attributes": "title: tab label; only inside Tabs",
        "required_attrs": ("title",),
        "optional_attrs": (),
        "places_in_the_page": "One panel of a Tabs",
        "reads_from": "The Markdown between its tags",
        "js": "enhance",
        "script": "aad_docs/tabs.js",
        "works_in": ".mdx",
        "parent": "Tabs",
        "template": "aad_docs/components/tab.html",
    },
    "Cards": {
        "tag": "Cards",
        "form": "container",
        "attributes": "none",
        "required_attrs": (),
        "optional_attrs": (),
        "places_in_the_page": "Grid of cards",
        "reads_from": "Its Card tags",
        "js": "none",
        "script": None,
        "works_in": ".mdx",
        "parent": None,
        "template": "aad_docs/components/cards.html",
    },
    "Card": {
        "tag": "Card",
        "form": "container",
        "attributes": "title: card heading; href: optional url; only inside Cards",
        "required_attrs": ("title",),
        "optional_attrs": ("href",),
        "url_attrs": ("href",),
        "places_in_the_page": "One card",
        "reads_from": "The Markdown between its tags",
        "js": "none",
        "script": None,
        "works_in": ".mdx",
        "parent": "Cards",
        "template": "aad_docs/components/card.html",
    },
    "details": {
        "tag": "details",
        "form": "container",
        "attributes": "open: optional, shows it open at first",
        "required_attrs": (),
        "optional_attrs": ("open",),
        "places_in_the_page": "Section the reader opens and closes",
        "reads_from": "The Markdown between its tags",
        "js": "none",
        "script": None,
        "works_in": ".md and .mdx",
        "parent": None,
        "template": "aad_docs/components/details.html",
    },
    "summary": {
        "tag": "summary",
        "form": "container",
        "attributes": "none; only inside details",
        "required_attrs": (),
        "optional_attrs": (),
        "places_in_the_page": "The line of a details that is always visible",
        "reads_from": "Its text",
        "js": "none",
        "script": None,
        "works_in": ".md and .mdx",
        "parent": "details",
        "template": "aad_docs/components/summary.html",
    },
}

_SELF_CLOSING_TAG_RE = re.compile(r"^<([A-Za-z][A-Za-z0-9]*)\s*(.*?)\s*/>\s*$")
_OPEN_TAG_RE = re.compile(r"^<([A-Za-z][A-Za-z0-9]*)(?:\s+(.*?))?\s*>\s*$")
_CLOSE_TAG_RE = re.compile(r"^</([A-Za-z][A-Za-z0-9]*)\s*>\s*$")
_INLINE_TAG_RE = re.compile(r"^<([A-Za-z][A-Za-z0-9]*)(?:\s+(.*?))?\s*>(.*?)</\1\s*>\s*$")


def is_safe_url(value: str) -> bool:
    """Return True if value uses http, https, mailto or is a relative path."""
    val = (value or "").strip()
    if not val or val.startswith("//"):
        return False
    parsed = urlparse(val)
    if not parsed.scheme:
        return True
    return parsed.scheme.lower() in ("http", "https", "mailto")


def parse_tag_attrs(raw_attrs: str | None) -> dict[str, str]:
    """Parse tag attributes (key="value" or standalone boolean attributes like open)."""
    if not raw_attrs or not raw_attrs.strip():
        return {}
    attrs: dict[str, str] = {}
    for token in shlex.split(raw_attrs.strip(), posix=True):
        if "=" in token:
            k, v = token.split("=", 1)
            attrs[k.strip()] = v
        else:
            attrs[token.strip()] = "true"
    return attrs


def resolve_safe_src(node_dir: Path, src: str) -> Path:
    """Resolve src inside node_dir, refusing any path that escapes node_dir."""
    root = node_dir.resolve()
    target = (root / src).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Tag src '{src}' leaves the node folder")
    if not target.is_file():
        raise FileNotFoundError(f"Tag src '{src}' does not exist in {root}")
    return target


def scripts_for(used_tags: Iterable[str], *, has_mermaid: bool = False) -> list[str]:
    """Return the static scripts a page needs, from the js flag of the components it uses."""
    scripts: list[str] = []
    if has_mermaid and "aad_docs/vendor/mermaid.min.js" not in scripts:
        scripts.append("aad_docs/vendor/mermaid.min.js")
    for tag_name in used_tags:
        spec = MDX_TAGS.get(tag_name)
        if spec and spec.get("script"):
            sc = spec["script"]
            if sc not in scripts:
                scripts.append(sc)
    return scripts


def _render_line_tag(tag_name: str, attrs: dict[str, str], node_dir: Path, lang_code: str) -> str:
    if tag_name == "Table":
        src = attrs.get("src", "")
        csv_path = resolve_safe_src(node_dir, src)
        pg = csv_reader.read(csv_path, node_dir, lang_code)
        return render_to_string("aad_docs/components/table.html", {"table": pg.content, "src": src})

    if tag_name == "Explorer":
        src = attrs.get("src", "")
        yml_path = resolve_safe_src(node_dir, src)
        pg = yaml_reader.read(yml_path, node_dir, lang_code)
        return render_to_string("aad_docs/components/explorer.html", {"codemap": pg.content, "src": src})

    if tag_name == "Flow":
        src = attrs.get("src", "")
        json_path = resolve_safe_src(node_dir, src)
        pg = json_reader.read(json_path, node_dir, lang_code)
        return render_to_string("aad_docs/components/flow.html", {"flow": pg.content, "src": src})

    if tag_name == "Model":
        model_ref = attrs.get("name", "")
        app_label, _, model_name = model_ref.partition(".")
        model_cls = apps.get_model(app_label, model_name)
        from aad_docs.codemap.models import describe_single_model

        model_info = describe_single_model(model_cls)
        return render_to_string("aad_docs/components/model.html", {"model": model_info})

    if tag_name == "ModelDiagram":
        app_label = attrs.get("app", "")
        from aad_docs.codemap.models import build_model_mermaid_diagram

        diagram_code = build_model_mermaid_diagram(app_label)
        return render_to_string("aad_docs/components/model_diagram.html", {"diagram": diagram_code, "app": app_label})

    if tag_name == "Screenshot":
        stem = attrs.get("name", "")
        alt = attrs.get("alt", stem)
        return render_to_string(
            "aad_docs/components/screenshot.html",
            {"name": stem, "alt": alt, "lang": lang_code},
        )

    raise ValueError(f"Unsupported line tag: {tag_name}")


def _render_mdx_lines(
    lines: list[str],
    node_dir: Path,
    lang_code: str,
    used_tags: list[str],
    source_path: Path,
) -> tuple[str, bool]:
    md, has_mermaid = make_markdown_renderer(source_path)
    out_lines: list[str] = []
    placeholders: dict[str, str] = {}
    in_fence = False
    i = 0
    counter = 0

    def add_placeholder(rendered_html: str) -> str:
        nonlocal counter
        key = f"AADDOCSMDXPLACEHOLDER{counter}END"
        counter += 1
        placeholders[key] = rendered_html
        return key

    while i < len(lines):
        line = lines[i]
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out_lines.append(line)
            i += 1
            continue
        if in_fence:
            out_lines.append(line)
            i += 1
            continue

        stripped = line.strip()

        # 1. Self-closing line tag: <Table src="..." />
        m_self = _SELF_CLOSING_TAG_RE.match(stripped)
        if m_self:
            tag_name, raw_attrs = m_self.groups()
            spec = MDX_TAGS.get(tag_name)
            if spec and spec["form"] == "line":
                attrs = parse_tag_attrs(raw_attrs)
                for req in spec.get("required_attrs", ()):
                    if req not in attrs or not attrs[req]:
                        raise ValueError(f"Tag <{tag_name} /> is missing required attribute '{req}'")
                used_tags.append(tag_name)
                frag = _render_line_tag(tag_name, attrs, node_dir, lang_code)
                out_lines.append(f"\n{add_placeholder(frag)}\n")
                i += 1
                continue

        # 2. Container tag opening on its own line: <Callout ...>, <Steps>, <Tabs>, <Cards>, <details>
        m_open = _OPEN_TAG_RE.match(stripped)
        if m_open:
            tag_name, raw_attrs = m_open.groups()
            spec = MDX_TAGS.get(tag_name)
            if spec and spec["form"] == "container" and spec.get("parent") is None:
                attrs = parse_tag_attrs(raw_attrs)
                for req in spec.get("required_attrs", ()):
                    if req not in attrs or not attrs[req]:
                        raise ValueError(f"Tag <{tag_name}> is missing required attribute '{req}'")
                allowed_vals = spec.get("allowed_values", {})
                for attr_k, valid_tuple in allowed_vals.items():
                    if attr_k in attrs and attrs[attr_k] not in valid_tuple:
                        raise ValueError(f"Invalid value '{attrs[attr_k]}' for {tag_name}.{attr_k}")

                i += 1
                inner_lines: list[str] = []
                depth = 1
                inner_fence = False
                while i < len(lines):
                    cur_line = lines[i]
                    if _FENCE_RE.match(cur_line):
                        inner_fence = not inner_fence
                    if not inner_fence:
                        cur_s = cur_line.strip()
                        m_nested_open = _OPEN_TAG_RE.match(cur_s)
                        if m_nested_open and m_nested_open.group(1) == tag_name:
                            depth += 1
                        m_close = _CLOSE_TAG_RE.match(cur_s)
                        if m_close and m_close.group(1) == tag_name:
                            depth -= 1
                            if depth == 0:
                                i += 1
                                break
                    inner_lines.append(cur_line)
                    i += 1

                if depth != 0:
                    raise ValueError(f"Unclosed container tag <{tag_name}>")

                used_tags.append(tag_name)
                frag = _render_container_tag(
                    tag_name, attrs, inner_lines, node_dir, lang_code, used_tags, source_path
                )
                out_lines.append(f"\n{add_placeholder(frag)}\n")
                continue

        out_lines.append(line)
        i += 1

    rendered = md.render("\n".join(out_lines))
    for key, frag in placeholders.items():
        rendered = rendered.replace(f"<p>{key}</p>", frag).replace(key, frag)
    return rendered, has_mermaid[0]


def _render_container_tag(
    tag_name: str,
    attrs: dict[str, str],
    inner_lines: list[str],
    node_dir: Path,
    lang_code: str,
    used_tags: list[str],
    source_path: Path,
) -> str:
    if tag_name == "Callout":
        body_html, _ = _render_mdx_lines(inner_lines, node_dir, lang_code, used_tags, source_path)
        return render_to_string(
            "aad_docs/components/callout.html",
            {
                "type": attrs.get("type", "note"),
                "title": attrs.get("title", ""),
                "body": body_html,
            },
        )

    if tag_name == "Steps":
        body_html, _ = _render_mdx_lines(inner_lines, node_dir, lang_code, used_tags, source_path)
        return render_to_string("aad_docs/components/steps.html", {"body": body_html})

    if tag_name == "details":
        summary_text = ""
        rest_lines: list[str] = []
        j = 0
        while j < len(inner_lines):
            s = inner_lines[j].strip()
            m_inline = _INLINE_TAG_RE.match(s)
            if m_inline and m_inline.group(1) == "summary" and not summary_text:
                used_tags.append("summary")
                summary_text = m_inline.group(3).strip()
                j += 1
                continue
            m_open = _OPEN_TAG_RE.match(s)
            if m_open and m_open.group(1) == "summary" and not summary_text:
                used_tags.append("summary")
                j += 1
                sum_parts: list[str] = []
                while j < len(inner_lines):
                    m_cl = _CLOSE_TAG_RE.match(inner_lines[j].strip())
                    if m_cl and m_cl.group(1) == "summary":
                        j += 1
                        break
                    sum_parts.append(inner_lines[j].strip())
                    j += 1
                summary_text = " ".join(sum_parts)
                continue
            rest_lines.append(inner_lines[j])
            j += 1
        body_html, _ = _render_mdx_lines(rest_lines, node_dir, lang_code, used_tags, source_path)
        return render_to_string(
            "aad_docs/components/details.html",
            {"open": "open" in attrs, "summary": summary_text, "body": body_html},
        )

    if tag_name in ("Tabs", "Cards"):
        child_tag = "Tab" if tag_name == "Tabs" else "Card"
        items: list[dict[str, Any]] = []
        j = 0
        while j < len(inner_lines):
            s = inner_lines[j].strip()
            if not s:
                j += 1
                continue
            m_open = _OPEN_TAG_RE.match(s)
            if not m_open or m_open.group(1) != child_tag:
                raise ValueError(f"Only <{child_tag}> is allowed inside <{tag_name}>, got: {s}")
            child_attrs = parse_tag_attrs(m_open.group(2))
            if "title" not in child_attrs or not child_attrs["title"]:
                raise ValueError(f"<{child_tag}> requires a 'title' attribute")
            href = child_attrs.get("href", "")
            if href and not is_safe_url(href):
                href = ""
            j += 1
            child_lines: list[str] = []
            closed = False
            while j < len(inner_lines):
                m_cl = _CLOSE_TAG_RE.match(inner_lines[j].strip())
                if m_cl and m_cl.group(1) == child_tag:
                    closed = True
                    j += 1
                    break
                child_lines.append(inner_lines[j])
                j += 1
            if not closed:
                raise ValueError(f"Unclosed <{child_tag}> inside <{tag_name}>")
            used_tags.append(child_tag)
            child_html, _ = _render_mdx_lines(child_lines, node_dir, lang_code, used_tags, source_path)
            items.append({"title": child_attrs["title"], "href": href, "body": child_html})

        template_name = "aad_docs/components/tabs.html" if tag_name == "Tabs" else "aad_docs/components/cards.html"
        return render_to_string(template_name, {"items": items})

    raise ValueError(f"Unsupported container tag: {tag_name}")


def read(file_path: Path, node_dir: Path | None = None, lang_code: str = "en") -> Page:
    """Render the Markdown of a .mdx with raw HTML disabled and replace each known tag with its component."""
    raw = file_path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw)

    raw_stem = file_path.name
    for suffix in (f".{lang_code}.mdx", ".mdx"):
        if raw_stem.endswith(suffix):
            raw_stem = raw_stem[: -len(suffix)]
            break
    slug = strip_numeric_prefix(raw_stem)
    title = extract_title(body, slug)

    effective_node_dir = (node_dir or file_path.parent).resolve()
    used_tags: list[str] = []
    html_content, has_mermaid = _render_mdx_lines(
        body.splitlines(), effective_node_dir, lang_code, used_tags, file_path
    )
    scripts = scripts_for(used_tags, has_mermaid=has_mermaid)

    return Page(
        slug=slug,
        title=title,
        kind="mdx",
        languages=[lang_code],
        variants={lang_code: str(file_path)},
        frontmatter=frontmatter,
        content=html_content,
        raw_stem=raw_stem,
        scripts=scripts,
    )
