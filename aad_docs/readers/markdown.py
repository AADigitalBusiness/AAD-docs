"""Markdown (.md) reader for AAD-docs.

Front-matter parsing adapted from django-md-cms / wagtail-shopify content_store (see decision 0014).
Renders .md to HTML with raw HTML disabled, keeping Mermaid blocks and reading semantic tags (details/summary).
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import yaml
from django.template.loader import render_to_string
from markdown_it import MarkdownIt

from aad_docs.discovery import strip_numeric_prefix
from aad_docs.nodes import Page

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_DETAILS_OPEN_RE = re.compile(r"^<details(?:\s+(open))?\s*>\s*$")
_DETAILS_CLOSE_RE = re.compile(r"^</details>\s*$")
_SUMMARY_INLINE_RE = re.compile(r"^<summary>(.*?)</summary>\s*$")
_SUMMARY_OPEN_RE = re.compile(r"^<summary>\s*$")
_SUMMARY_CLOSE_RE = re.compile(r"^</summary>\s*$")


def split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body_without_frontmatter)."""
    if not raw.startswith("---\n"):
        return {}, raw
    end_idx = raw.find("\n---\n", 4)
    if end_idx == -1:
        return {}, raw
    fm_text = raw[4:end_idx]
    body = raw[end_idx + 5 :]
    try:
        parsed = yaml.safe_load(fm_text)
        if isinstance(parsed, dict):
            return {str(k): v for k, v in parsed.items()}, body
    except yaml.YAMLError:
        pass
    return {}, body


def extract_title(body: str, fallback: str) -> str:
    """Extract the first level-1 Markdown heading as title."""
    in_fence = False
    for line in body.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def make_markdown_renderer() -> tuple[MarkdownIt, list[bool]]:
    """Create a MarkdownIt instance with raw HTML disabled and Mermaid fence support."""
    has_mermaid = [False]
    md = MarkdownIt("commonmark", {"html": False}).enable("table")

    def render_fence(self: Any, tokens: Any, idx: int, options: Any, env: Any) -> str:
        tok = tokens[idx]
        info = (tok.info or "").strip()
        if info == "mermaid":
            has_mermaid[0] = True
            return f'<pre class="mermaid">{html.escape(tok.content)}</pre>\n'
        lang_cls = f' class="language-{html.escape(info)}"' if info else ""
        return f"<pre><code{lang_cls}>{html.escape(tok.content)}</code></pre>\n"

    md.add_render_rule("fence", render_fence)
    return md, has_mermaid


def _render_md_with_details(body: str) -> tuple[str, bool]:
    """Render Markdown while supporting semantic <details> and <summary> blocks outside code fences."""
    md, has_mermaid = make_markdown_renderer()
    lines = body.splitlines()
    out_lines: list[str] = []
    placeholders: dict[str, str] = {}
    in_fence = False
    i = 0
    counter = 0

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

        m_open = _DETAILS_OPEN_RE.match(line.strip())
        if m_open:
            is_open = bool(m_open.group(1))
            i += 1
            summary_text = ""
            inner_lines: list[str] = []
            closed = False
            while i < len(lines):
                cur = lines[i].strip()
                if _DETAILS_CLOSE_RE.match(cur):
                    closed = True
                    i += 1
                    break
                m_sum = _SUMMARY_INLINE_RE.match(cur)
                if m_sum and not summary_text:
                    summary_text = m_sum.group(1).strip()
                    i += 1
                    continue
                if _SUMMARY_OPEN_RE.match(cur) and not summary_text:
                    i += 1
                    sum_parts: list[str] = []
                    while i < len(lines) and not _SUMMARY_CLOSE_RE.match(lines[i].strip()):
                        sum_parts.append(lines[i].strip())
                        i += 1
                    if i < len(lines):
                        i += 1
                    summary_text = " ".join(sum_parts)
                    continue
                inner_lines.append(lines[i])
                i += 1

            if closed:
                inner_html, inner_mermaid = _render_md_with_details("\n".join(inner_lines))
                if inner_mermaid:
                    has_mermaid[0] = True
                token_key = f"AADDOCSDETAILSPLACEHOLDER{counter}END"
                counter += 1
                placeholders[token_key] = render_to_string(
                    "aad_docs/components/details.html",
                    {
                        "open": is_open,
                        "summary": summary_text,
                        "body": inner_html,
                    },
                )
                out_lines.append(f"\n{token_key}\n")
                continue

        out_lines.append(line)
        i += 1

    rendered = md.render("\n".join(out_lines))
    for key, frag in placeholders.items():
        rendered = rendered.replace(f"<p>{key}</p>", frag).replace(key, frag)
    return rendered, has_mermaid[0]


def read(file_path: Path, node_dir: Path | None = None, lang_code: str = "en") -> Page:
    """Render a .md file to HTML with raw HTML disabled, keeping Mermaid blocks and semantic tags."""
    raw = file_path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw)

    raw_stem = file_path.name
    for suffix in (f".{lang_code}.md", ".md"):
        if raw_stem.endswith(suffix):
            raw_stem = raw_stem[: -len(suffix)]
            break
    slug = strip_numeric_prefix(raw_stem)
    title = extract_title(body, slug)

    html_content, has_mermaid = _render_md_with_details(body)
    scripts = ["aad_docs/vendor/mermaid.min.js"] if has_mermaid else []

    return Page(
        slug=slug,
        title=title,
        kind="md",
        languages=[lang_code],
        variants={lang_code: str(file_path)},
        frontmatter=frontmatter,
        content=html_content,
        raw_stem=raw_stem,
        scripts=scripts,
    )
