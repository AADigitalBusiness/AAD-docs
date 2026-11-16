"""Documentation validation rules (D001 to D065) for AAD-docs.

Owner of checks.csv (see decision 0012).
"""
from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.apps import apps

from aad_docs.codemap.models import clean_model_docstring, is_default_model_docstring
from aad_docs.conf import get_settings
from aad_docs.discovery import (
    READABLE_EXTENSIONS,
    _load_node_from_init,
    parse_doc_filename,
    strip_numeric_prefix,
)
from aad_docs.generated import GeneratedManifest
from aad_docs.nodes import Node
from aad_docs.readers.markdown import _FENCE_RE, split_frontmatter
from aad_docs.readers.mdx import (
    MDX_TAGS,
    _CLOSE_TAG_RE,
    _INLINE_TAG_RE,
    _OPEN_TAG_RE,
    _SELF_CLOSING_TAG_RE,
    is_safe_url,
    parse_tag_attrs,
    resolve_safe_src,
)


@dataclass(frozen=True)
class CheckFinding:
    """One validation finding reported by run_checks."""

    code: str
    path: str
    message: str


CHECKS: dict[str, dict[str, str]] = {
    "D001": {
        "code": "D001",
        "finding": "An installed app has no docs/ folder",
        "detected_by": "An app in INSTALLED_APPS, not in EXCLUDE_APPS, has no folder named docs",
        "fix": "Create <app>/docs/ with an __init__.py or add the app to EXCLUDE_APPS",
    },
    "D002": {
        "code": "D002",
        "finding": "A docs/ folder or subfolder has no __init__.py",
        "detected_by": "A docs/ folder or a subfolder of a node has no __init__.py; a folder named after a model slug is exempt",
        "fix": "Add an __init__.py; without it the folder is not a node",
    },
    "D003": {
        "code": "D003",
        "finding": "A node's __init__.py fails to import or declares no valid node",
        "detected_by": "Importing __init__.py raises, or `node` is missing or is not a Node",
        "fix": "Fix the error; the node is skipped until then",
    },
    "D004": {
        "code": "D004",
        "finding": "A name in pages matches no file or child node",
        "detected_by": "A name in `pages` matches no file stem, slug or child folder",
        "fix": "Fix the name or remove it",
    },
    "D005": {
        "code": "D005",
        "finding": "A link points to a file that does not exist",
        "detected_by": "A relative link in a .md or .mdx resolves to no file",
        "fix": "Fix the link",
    },
    "D006": {
        "code": "D006",
        "finding": "A file has an extension the app does not read",
        "detected_by": "A file outside assets/ has an extension the app does not read",
        "fix": "Move it to assets/ if it is an image, else remove it",
    },
    "D007": {
        "code": "D007",
        "finding": "A section and a model of the same app produce the same slug",
        "detected_by": "The slug of a section folder equals the model_name of a model of the same app",
        "fix": "Rename the section folder. Until then the section answers at that address and the model page does not",
    },
    "D008": {
        "code": "D008",
        "finding": "Two files in the same folder produce the same slug",
        "detected_by": "Two files of one folder have the same stem once numeric prefix, language suffix and extension are removed",
        "fix": "Rename one of them",
    },
    "D010": {
        "code": "D010",
        "finding": "A Spanish page was synced before its source last changed",
        "detected_by": "The synced date is earlier than `git log -1 --format=%cs` of the source file; skipped with a notice when there is no git repository",
        "fix": "Update the Spanish page and its synced date",
    },
    "D011": {
        "code": "D011",
        "finding": "A Spanish page has no source and synced header",
        "detected_by": "A page named *.es.* lacks source or synced in its header",
        "fix": "Add the header",
    },
    "D012": {
        "code": "D012",
        "finding": "A Spanish page names a source that does not exist",
        "detected_by": "The source named in the header is not a file of the same folder",
        "fix": "Fix the source name",
    },
    "D020": {
        "code": "D020",
        "finding": "A model has no docstring",
        "detected_by": "__doc__ is empty or is the one Django generates, Model(field, ...)",
        "fix": "Add a docstring that says what the model represents",
    },
    "D021": {
        "code": "D021",
        "finding": "A model field has no help_text",
        "detected_by": "help_text is empty on a local field; the automatic primary key is exempt",
        "fix": "Add help_text",
    },
    "D030": {
        "code": "D030",
        "finding": "A .md repeats a help_text or a model docstring",
        "detected_by": "The normalized text of a help_text of 20 characters or more, or of a docstring of 40 or more, appears in a page",
        "fix": "Remove the copy and reference the model",
    },
    "D031": {
        "code": "D031",
        "finding": "A .md contains a hand-written table of model fields",
        "detected_by": "A Markdown table whose header defines fields and that names two or more real fields of a model of the app",
        "fix": "Remove it; the field table is generated",
    },
    "D032": {
        "code": "D032",
        "finding": "The same paragraph appears in two pages",
        "detected_by": "A plain paragraph of 120 characters or 20 words, outside code, headings and tables, appears in two pages once lowercased, with spaces collapsed and no punctuation",
        "fix": "Keep it in its owner and link from the other",
    },
    "D040": {
        "code": "D040",
        "finding": "A generated file was edited by hand",
        "detected_by": "The hash of a generated file differs from .generated.yml",
        "fix": "Restore it or delete it and run docs_codemap",
    },
    "D041": {
        "code": "D041",
        "finding": "A generated file is out of date with the code",
        "detected_by": "Regenerating gives a file different from the one on disk",
        "fix": "Run docs_codemap",
    },
    "D050": {
        "code": "D050",
        "finding": "A page does not open with a purpose line",
        "detected_by": "No paragraph follows the title directly",
        "fix": "Add one line under the title that says what the reader gets",
    },
    "D051": {
        "code": "D051",
        "finding": "A .md page has no diagram",
        "detected_by": "A .md page has no Mermaid block; .mdx pages are exempt",
        "fix": "Add a Mermaid diagram after the purpose line",
    },
    "D052": {
        "code": "D052",
        "finding": "A guide step with interface has no screenshot",
        "detected_by": "In 05-guides/, a numbered step under ## Steps or ## Pasos has no CLI block, image or Screenshot tag and names an interface term: click, open, select, button, menu, screen, form, or their Spanish equivalents",
        "fix": "Run docs_screenshots",
    },
    "D060": {
        "code": "D060",
        "finding": "A .mdx uses a tag that is not listed in mdx-tags.csv",
        "detected_by": "A tag outside code blocks and inline code is not in mdx-tags.csv",
        "fix": "Use a listed tag or remove it",
    },
    "D061": {
        "code": "D061",
        "finding": "A tag points to a file or a model that does not exist",
        "detected_by": "The src or name of a tag resolves to no file inside the node folder or to no model",
        "fix": "Fix its src or name",
    },
    "D062": {
        "code": "D062",
        "finding": "A .mdx contains import or export or a JavaScript expression",
        "detected_by": "import, export or a JavaScript expression appears outside code blocks and inline code",
        "fix": "Remove it; the app compiles nothing",
    },
    "D063": {
        "code": "D063",
        "finding": "A container tag is not closed, is closed out of order, or sits in a parent the registry does not allow",
        "detected_by": "Tags are matched as a stack; Tab is valid only inside Tabs and Card only inside Cards",
        "fix": "Close the tag, or move it into its parent",
    },
    "D064": {
        "code": "D064",
        "finding": "A tag lacks a required attribute or has a value the registry does not list",
        "detected_by": "Each attribute is checked against the registry: required, and for type the values note, tip, warning and danger, and for an attribute of type url only the schemes http, https and mailto or a relative path",
        "fix": "Add the attribute or use a listed value",
    },
    "D065": {
        "code": "D065",
        "finding": "A page contains an HTML tag that is not in the registry; it shows as text",
        "detected_by": "A lowercase HTML tag outside code blocks and inline code whose name the registry does not list",
        "fix": "Use a component of the registry or remove the tag",
    },
}

_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_UI_TERMS_RE = re.compile(
    r"\b(click|open|select|button|menu|screen|form|haz clic|clic|abre|selecciona|botón|menú|pantalla|formulario)\b",
    re.IGNORECASE,
)
_LOWER_HTML_TAG_RE = re.compile(r"</?([a-z][a-z0-9]*)\b[^>]*>")
_ANY_TAG_TOKEN_RE = re.compile(r"^\s*<(/?)([A-Za-z][A-Za-z0-9]*)(?:\s+(.*?))?\s*(/?)>\s*$")


def _strip_code(text: str) -> str:
    """Return text with fenced code blocks and inline code spans replaced by blank lines/spaces."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence:
            out.append("")
        else:
            out.append(_INLINE_CODE_RE.sub(" ", line))
    return "\n".join(out)


def _normalize_prose(text: str) -> str:
    no_punct = _PUNCT_RE.sub(" ", text.lower())
    return re.sub(r"\s+", " ", no_punct).strip()


def _git_last_modified_date(file_path: Path) -> str | None:
    try:
        res = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(file_path)],
            cwd=str(file_path.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None


def _check_init_declares_valid_node(init_path: Path) -> tuple[Node | None, bool]:
    """Return (Node, True) if __init__.py imports cleanly AND defines a valid Node (or is empty only when allowed)."""
    try:
        src = init_path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(init_path))
        has_node_assign = any(
            isinstance(stmt, (ast.Assign, ast.AnnAssign))
            and any(isinstance(t, ast.Name) and t.id == "node" for t in (stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]))
            for stmt in tree.body
        )
    except Exception:
        return None, False

    node, err = _load_node_from_init(init_path)
    if err is not None or node is None or not has_node_assign:
        return None, False
    return node, True


def _check_md_or_mdx_page(
    file_path: Path,
    node_dir: Path,
    app_models: list[Any],
    languages: list[str],
    findings: list[CheckFinding],
    paragraphs_seen: dict[tuple[str, str], str],
) -> None:
    rel = str(file_path)
    raw = file_path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw)
    ext = file_path.suffix.lower()
    default_lang = languages[0] if languages else "en"

    parsed_name = parse_doc_filename(file_path.name, languages)
    page_lang = parsed_name[2] if parsed_name else default_lang

    # D010, D011, D012: non-default language variant header checks
    if page_lang != default_lang:
        src_name = frontmatter.get("source")
        synced_val = frontmatter.get("synced")
        if not src_name or not synced_val:
            findings.append(CheckFinding("D011", rel, "Spanish page has no source and synced header"))
        else:
            src_path = file_path.parent / str(src_name)
            if not src_path.is_file():
                findings.append(CheckFinding("D012", rel, f"Spanish page names missing source '{src_name}'"))
            else:
                git_date = _git_last_modified_date(src_path)
                if git_date and str(synced_val) < git_date:
                    findings.append(
                        CheckFinding("D010", rel, f"Spanish page synced ({synced_val}) before source changed ({git_date})")
                    )

    stripped_code_body = _strip_code(body)

    # D005: broken relative links
    for m in _LINK_RE.finditer(stripped_code_body):
        target_link = m.group(1).strip()
        if target_link.startswith(("http://", "https://", "mailto:", "/")):
            continue
        target_path = (file_path.parent / target_link).resolve()
        if not target_path.exists():
            findings.append(CheckFinding("D005", rel, f"Broken relative link '{target_link}'"))

    # D050: purpose line directly after # Title
    lines = body.splitlines()
    title_idx = None
    for idx, ln in enumerate(lines):
        if ln.strip().startswith("# "):
            title_idx = idx
            break
    if title_idx is None:
        findings.append(CheckFinding("D050", rel, "Page has no level-1 title and purpose line"))
    else:
        next_non_empty = None
        for ln in lines[title_idx + 1 :]:
            s = ln.strip()
            if s:
                next_non_empty = s
                break
        if (
            not next_non_empty
            or next_non_empty.startswith(("#", "```", "~~~", "|", "- ", "* ", "<"))
            or re.match(r"^\d+\.", next_non_empty)
        ):
            findings.append(CheckFinding("D050", rel, "Page does not open with a purpose line directly under the title"))

    # D051: .md page has no Mermaid diagram (.mdx exempt)
    if ext == ".md":
        has_mermaid = bool(re.search(r"^\s*(?:`{3,}|~{3,})mermaid\b", body, re.MULTILINE))
        if not has_mermaid:
            findings.append(CheckFinding("D051", rel, "Markdown page has no Mermaid diagram"))

    # D030 & D031: model docstring / help_text repetition and hand-written model field table
    norm_page_text = _normalize_prose(stripped_code_body)
    for model_cls in app_models:
        doc = clean_model_docstring(model_cls)
        if len(doc) >= 40:
            norm_doc = _normalize_prose(doc)
            if norm_doc and norm_doc in norm_page_text:
                findings.append(CheckFinding("D030", rel, f"Page repeats docstring of {model_cls.__name__}"))
        for f in model_cls._meta.local_fields:
            ht = str(getattr(f, "help_text", "") or "").strip()
            if len(ht) >= 20:
                norm_ht = _normalize_prose(ht)
                if norm_ht and norm_ht in norm_page_text:
                    findings.append(CheckFinding("D030", rel, f"Page repeats help_text of {model_cls.__name__}.{f.name}"))

        # D031: Markdown table whose header defines fields and names >= 2 real fields of model_cls
        real_field_names = {f.name.lower() for f in model_cls._meta.local_fields if not getattr(f, "primary_key", False)}
        in_table = False
        table_defines_fields = False
        matched_fields: set[str] = set()
        for ln in stripped_code_body.splitlines():
            s = ln.strip()
            if s.startswith("|") and s.endswith("|"):
                cells = [c.strip().lower().strip("`*") for c in s.strip("|").split("|")]
                if not in_table:
                    in_table = True
                    header_set = set(cells)
                    if ("field" in header_set or "campo" in header_set or "name" in header_set) and (
                        "type" in header_set or "tipo" in header_set or "description" in header_set or "help_text" in header_set
                    ):
                        table_defines_fields = True
                elif table_defines_fields and cells and not all(set(c) <= {"-", ":"} for c in cells):
                    first_col = cells[0]
                    if first_col in real_field_names:
                        matched_fields.add(first_col)
            else:
                if in_table and table_defines_fields and len(matched_fields) >= 2:
                    findings.append(CheckFinding("D031", rel, f"Hand-written field table for {model_cls.__name__}"))
                in_table = False
                table_defines_fields = False
                matched_fields = set()
        if in_table and table_defines_fields and len(matched_fields) >= 2:
            findings.append(CheckFinding("D031", rel, f"Hand-written field table for {model_cls.__name__}"))

    # D032: duplicate plain paragraph across pages (>= 120 chars or >= 20 words)
    chunks = re.split(r"\n\s*\n", stripped_code_body)
    for chunk in chunks:
        s = chunk.strip()
        if not s or s.startswith(("#", "|", "- ", "* ", "<", ">")) or re.match(r"^\d+\.", s):
            continue
        if s.startswith("**Status:") or s.startswith("Read this page") or s.startswith("Follow this guide"):
            continue
        norm_p = _normalize_prose(s)
        words = norm_p.split()
        if len(norm_p) >= 120 or len(words) >= 20:
            key = (page_lang, norm_p)
            prev = paragraphs_seen.get(key)
            if prev and prev != rel:
                findings.append(CheckFinding("D032", rel, f"Duplicate paragraph also in {prev}"))
            else:
                paragraphs_seen[key] = rel

    # D052: guide step with interface term has no screenshot
    if file_path.parent.name.endswith("guides"):
        steps_match = re.search(r"^##\s+(?:Steps|Pasos)\s*$(.*?)(?:^##\s+|\Z)", body, re.MULTILINE | re.DOTALL)
        if steps_match:
            steps_block = steps_match.group(1)
            step_items = re.split(r"(?m)^\d+\.\s+", steps_block)[1:]
            for step_txt in step_items:
                has_code_block = bool(re.search(r"(`{3,}|~{3,})", step_txt))
                has_img = bool(re.search(r"!\[[^\]]*\]\([^)]+\)", step_txt)) or ("<Screenshot" in step_txt)
                if not has_code_block and not has_img and _UI_TERMS_RE.search(step_txt):
                    findings.append(CheckFinding("D052", rel, "Guide step with interface term has no screenshot"))
                    break

    # D065: lowercase HTML tag not in MDX_TAGS (applies to .md and .mdx)
    for m_html in _LOWER_HTML_TAG_RE.finditer(stripped_code_body):
        tag_nm = m_html.group(1)
        if tag_nm not in MDX_TAGS:
            findings.append(CheckFinding("D065", rel, f"Unlisted HTML tag <{tag_nm}>"))

    # D060, D061, D062, D063, D064 on .mdx (and container stack on .md for details/summary)
    if ext == ".mdx":
        _check_mdx_rules(file_path, node_dir, stripped_code_body, findings)


def _validate_tag_attributes_and_targets(
    tag_name: str,
    raw_attrs: str | None,
    file_path: Path,
    node_dir: Path,
    findings: list[CheckFinding],
) -> None:
    rel = str(file_path)
    spec = MDX_TAGS[tag_name]
    try:
        attrs = parse_tag_attrs(raw_attrs)
    except Exception:
        findings.append(CheckFinding("D064", rel, f"Malformed attributes on <{tag_name}>"))
        return

    allowed_attr_names = set(spec.get("required_attrs", ())) | set(spec.get("optional_attrs", ()))
    for req in spec.get("required_attrs", ()):
        if req not in attrs or not attrs[req].strip():
            findings.append(CheckFinding("D064", rel, f"Tag <{tag_name}> lacks required attribute '{req}'"))

    for k in attrs:
        if k not in allowed_attr_names:
            findings.append(CheckFinding("D064", rel, f"Tag <{tag_name}> has unlisted attribute '{k}'"))

    for attr_k, valid_vals in spec.get("allowed_values", {}).items():
        if attr_k in attrs and attrs[attr_k] not in valid_vals:
            findings.append(CheckFinding("D064", rel, f"Tag <{tag_name}> has invalid value '{attrs[attr_k]}' for '{attr_k}'"))

    for url_attr in spec.get("url_attrs", ()):
        if url_attr in attrs and not is_safe_url(attrs[url_attr]):
            findings.append(CheckFinding("D064", rel, f"Tag <{tag_name}> has unsafe URL in '{url_attr}'"))

    # D061: target existence for src / name / app
    if "src" in attrs and attrs["src"]:
        try:
            resolve_safe_src(node_dir, attrs["src"])
        except Exception:
            findings.append(CheckFinding("D061", rel, f"Tag <{tag_name}> src '{attrs['src']}' does not exist in node"))

    if tag_name == "Model" and attrs.get("name"):
        app_lbl, _, mdl_name = attrs["name"].partition(".")
        try:
            apps.get_model(app_lbl, mdl_name)
        except Exception:
            findings.append(CheckFinding("D061", rel, f"Tag <Model> references unknown model '{attrs['name']}'"))

    if tag_name == "ModelDiagram" and attrs.get("app"):
        try:
            apps.get_app_config(attrs["app"])
        except LookupError:
            findings.append(CheckFinding("D061", rel, f"Tag <ModelDiagram> references unknown app '{attrs['app']}'"))

    if tag_name == "Screenshot" and attrs.get("name"):
        stem = attrs["name"]
        assets_dir = node_dir / "assets"
        if not assets_dir.is_dir() or not list(assets_dir.glob(f"{stem}*")):
            findings.append(CheckFinding("D061", rel, f"Tag <Screenshot> references missing asset '{stem}'"))


def _check_mdx_rules(
    file_path: Path,
    node_dir: Path,
    stripped_code_body: str,
    findings: list[CheckFinding],
) -> None:
    rel = str(file_path)
    stack: list[str] = []

    for ln in stripped_code_body.splitlines():
        s = ln.strip()
        if not s:
            continue

        # D062: import, export or JS expression { ... }
        if re.match(r"^(import|export)\s+", s) or re.search(r"\{[^}]+\}", s):
            findings.append(CheckFinding("D062", rel, "MDX contains import, export or JavaScript expression"))

        # Inline open+close on same line (e.g. <summary>Text</summary>)
        m_inline = _INLINE_TAG_RE.match(s)
        if m_inline:
            tag_name, raw_attrs, _ = m_inline.groups()
            if tag_name not in MDX_TAGS:
                if tag_name[0].isupper():
                    findings.append(CheckFinding("D060", rel, f"Unknown MDX tag <{tag_name}>"))
                continue
            spec = MDX_TAGS[tag_name]
            req_parent = spec.get("parent")
            if req_parent and (not stack or stack[-1] != req_parent):
                findings.append(CheckFinding("D063", rel, f"Tag <{tag_name}> must be inside <{req_parent}>"))
            _validate_tag_attributes_and_targets(tag_name, raw_attrs, file_path, node_dir, findings)
            continue

        m_tag = _ANY_TAG_TOKEN_RE.match(s)
        if not m_tag:
            continue
        is_closing, tag_name, raw_attrs, is_self_closing = m_tag.groups()

        if tag_name not in MDX_TAGS:
            if tag_name[0].isupper():
                findings.append(CheckFinding("D060", rel, f"Unknown MDX tag <{tag_name}>"))
            continue

        spec = MDX_TAGS[tag_name]
        req_parent = spec.get("parent")

        if is_self_closing:
            if spec["form"] == "container":
                findings.append(CheckFinding("D063", rel, f"Container tag <{tag_name}> cannot be self-closing"))
            if req_parent and (not stack or stack[-1] != req_parent):
                findings.append(CheckFinding("D063", rel, f"Tag <{tag_name}> must be inside <{req_parent}>"))
            _validate_tag_attributes_and_targets(tag_name, raw_attrs, file_path, node_dir, findings)
        elif is_closing:
            if not stack or stack[-1] != tag_name:
                findings.append(CheckFinding("D063", rel, f"Closing tag </{tag_name}> out of order"))
            else:
                stack.pop()
        else:
            if spec["form"] == "line":
                findings.append(CheckFinding("D063", rel, f"Line tag <{tag_name}> must be self-closing"))
                continue
            if req_parent and (not stack or stack[-1] != req_parent):
                findings.append(CheckFinding("D063", rel, f"Tag <{tag_name}> must be inside <{req_parent}>"))
            stack.append(tag_name)
            _validate_tag_attributes_and_targets(tag_name, raw_attrs, file_path, node_dir, findings)

    if stack:
        findings.append(CheckFinding("D063", rel, f"Unclosed container tag(s): {', '.join(stack)}"))


def _check_docs_folder(
    docs_dir: Path,
    app_config: Any | None,
    languages: list[str],
    findings: list[CheckFinding],
    paragraphs_seen: dict[tuple[str, str], str],
) -> None:
    docs_dir = docs_dir.resolve()
    app_models = list(app_config.get_models()) if app_config is not None else []
    model_slugs = {m._meta.model_name for m in app_models}

    init_path = docs_dir / "__init__.py"
    if not init_path.is_file():
        findings.append(CheckFinding("D002", str(docs_dir), "Documentation folder has no __init__.py"))
        return

    node, valid_node = _check_init_declares_valid_node(init_path)
    if not valid_node or node is None:
        findings.append(CheckFinding("D003", str(init_path), "Node __init__.py fails to import or declares no valid node"))
        return

    # Check generated files (D040, D041) if .generated.yml exists
    manifest = GeneratedManifest(docs_dir)
    for edited_rel in manifest.hand_edited_files():
        findings.append(CheckFinding("D040", str(docs_dir / edited_rel), f"Generated file '{edited_rel}' was edited by hand"))

    if manifest.entries and app_config is not None:
        from aad_docs.codemap.writer import (
            build_codemap_payload,
            build_model_field_tables,
            build_reference_tables_for_aad_docs,
        )
        import yaml

        expected_files: dict[str, str] = {
            "code-map.yml": yaml.safe_dump(build_codemap_payload(app_config.label), sort_keys=False, allow_unicode=True)
        }
        if app_config.label == "aad_docs":
            expected_files.update(build_reference_tables_for_aad_docs())
        else:
            expected_files.update(build_model_field_tables(app_config.label))

        for rel_p, expected_txt in expected_files.items():
            if rel_p in manifest.entries:
                disk_file = docs_dir / rel_p
                if not disk_file.is_file() or disk_file.read_text(encoding="utf-8") != expected_txt:
                    findings.append(CheckFinding("D041", str(disk_file), f"Generated file '{rel_p}' is out of date with the code"))

    # Inspect entries in docs_dir
    slug_to_kinds: dict[str, set[str]] = {}
    valid_page_names: set[str] = set()

    for entry in sorted(docs_dir.iterdir(), key=lambda p: p.name):
        if entry.name.startswith(".") or entry.name in ("__init__.py", "__pycache__", "assets"):
            continue
        if entry.is_dir():
            if entry.name in model_slugs and not (entry / "__init__.py").is_file():
                # Model folder is exempt from D002; still check its pages
                for m_entry in sorted(entry.iterdir(), key=lambda p: p.name):
                    if m_entry.is_file() and m_entry.suffix.lower() in (".md", ".mdx"):
                        _check_md_or_mdx_page(m_entry, docs_dir, app_models, languages, findings, paragraphs_seen)
                continue

            sub_init = entry / "__init__.py"
            if not sub_init.is_file():
                findings.append(CheckFinding("D002", str(entry), f"Subfolder '{entry.name}' has no __init__.py"))
                continue

            sub_node, sub_valid = _check_init_declares_valid_node(sub_init)
            if not sub_valid or sub_node is None:
                findings.append(CheckFinding("D003", str(sub_init), "Child node __init__.py fails to import or declares no valid node"))
                continue

            sub_slug = sub_node.slug or strip_numeric_prefix(entry.name).replace("_", "-")
            valid_page_names.add(entry.name)
            valid_page_names.add(sub_slug)

            if sub_slug in model_slugs:
                findings.append(CheckFinding("D007", str(entry), f"Section '{sub_slug}' collides with model slug '{sub_slug}'"))

            _check_docs_folder(entry, app_config, languages, findings, paragraphs_seen)
        else:
            parsed = parse_doc_filename(entry.name, languages)
            if parsed is None:
                findings.append(CheckFinding("D006", str(entry), f"Unsupported file extension '{entry.suffix}'"))
                continue
            raw_stem, slug, lang, kind = parsed
            valid_page_names.add(raw_stem)
            valid_page_names.add(slug)
            slug_to_kinds.setdefault(slug, set()).add(f"{raw_stem}.{kind}")

            if kind in ("md", "mdx"):
                _check_md_or_mdx_page(entry, docs_dir, app_models, languages, findings, paragraphs_seen)

    # D008: two files in the same folder produce the same slug
    for slug, kind_stems in slug_to_kinds.items():
        if len(kind_stems) > 1:
            findings.append(CheckFinding("D008", str(docs_dir), f"Multiple files in {docs_dir.name} produce the same slug '{slug}'"))

    # D004: name in node.pages matches no file or child node
    if node.pages is not None:
        for listed in node.pages:
            if listed not in valid_page_names:
                findings.append(CheckFinding("D004", str(init_path), f"Name '{listed}' in pages matches no file or child node"))


def run_checks(
    app_labels: list[str] | None = None,
    *,
    extra_doc_dirs: list[Path] | None = None,
) -> list[CheckFinding]:
    """Run every docs_check rule and return the findings."""
    cfg = get_settings()
    exclude = set(cfg.get("EXCLUDE_APPS") or [])
    languages: list[str] = list(cfg.get("LANGUAGES") or ["en", "es"])
    findings: list[CheckFinding] = []
    paragraphs_seen: dict[tuple[str, str], str] = {}

    if extra_doc_dirs is not None:
        for d in extra_doc_dirs:
            _check_docs_folder(Path(d), None, languages, findings, paragraphs_seen)
        return findings

    if not app_labels:
        root_dir = cfg.get("ROOT")
        if root_dir and Path(root_dir).exists():
            _check_docs_folder(Path(root_dir), None, languages, findings, paragraphs_seen)

    for ac in apps.get_app_configs():
        if ac.name.startswith("django.contrib.") or ac.label in exclude:
            continue
        if app_labels and ac.label not in app_labels:
            continue

        app_path = Path(ac.path)
        docs_dir = app_path / "docs"
        if not docs_dir.is_dir():
            findings.append(CheckFinding("D001", str(app_path), f"App '{ac.label}' has no docs/ folder"))
            continue

        # D020 & D021: model docstrings and field help_text
        for model_cls in ac.get_models():
            if is_default_model_docstring(model_cls):
                findings.append(CheckFinding("D020", f"{ac.label}.{model_cls.__name__}", f"Model {model_cls.__name__} has no docstring"))
            for f in model_cls._meta.local_fields:
                if getattr(f, "primary_key", False) and f.get_internal_type() in ("AutoField", "BigAutoField", "SmallAutoField"):
                    continue
                if not str(getattr(f, "help_text", "") or "").strip():
                    findings.append(
                        CheckFinding("D021", f"{ac.label}.{model_cls.__name__}.{f.name}", f"Field {model_cls.__name__}.{f.name} has no help_text")
                    )

        _check_docs_folder(docs_dir, ac, languages, findings, paragraphs_seen)

    return findings
