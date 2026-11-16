"""Readers registry and dispatcher for AAD-docs.

Owner of file-types.csv.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from aad_docs.language import get_active_language, pick_variant
from aad_docs.nodes import Page


FILE_TYPES_SPEC: tuple[dict[str, str], ...] = (
    {
        "extension": ".md",
        "holds": "Pages",
        "written_by": "A person",
        "reader": "readers/markdown.py",
        "shown_as": "Text with Mermaid diagrams, collapsible sections and screenshots",
    },
    {
        "extension": ".mdx",
        "holds": "Pages that use visual components or embed a piece: callout, steps, tabs, cards, table, flow, model",
        "written_by": "A person",
        "reader": "readers/mdx.py",
        "shown_as": "Text with the components and interactive pieces inside the page",
    },
    {
        "extension": ".yml",
        "holds": "Structured data: the code map, a glossary",
        "written_by": "A command",
        "reader": "readers/yaml.py",
        "shown_as": "Click-through explorer",
    },
    {
        "extension": ".csv",
        "holds": "Tables: fields, parameters, permissions",
        "written_by": "A command",
        "reader": "readers/csv.py",
        "shown_as": "Table that sorts and filters",
    },
    {
        "extension": ".json",
        "holds": "Data for interactive pieces: flows, API schemas",
        "written_by": "A person or a command",
        "reader": "readers/json.py",
        "shown_as": "Step-by-step simulator or viewer",
    },
    {
        "extension": ".png in assets/",
        "holds": "Screenshots",
        "written_by": "docs_screenshots",
        "reader": "none; served as a file",
        "shown_as": "Image inside a .md",
    },
)

READERS: dict[str, Callable[[Path, Path | None, str], Page]] = {}


def _ensure_readers_registered() -> None:
    if READERS:
        return
    from aad_docs.readers import csv as csv_reader
    from aad_docs.readers import json as json_reader
    from aad_docs.readers import markdown as md_reader
    from aad_docs.readers import mdx as mdx_reader
    from aad_docs.readers import yaml as yaml_reader

    READERS[".md"] = md_reader.read
    READERS[".mdx"] = mdx_reader.read
    READERS[".yml"] = yaml_reader.read
    READERS[".yaml"] = yaml_reader.read
    READERS[".csv"] = csv_reader.read
    READERS[".json"] = json_reader.read


def read_page(
    target: Page | str | Path,
    lang_code: str | None = None,
    node_dir: Path | None = None,
) -> Page:
    """Pick the reader for a file extension and return a populated Page."""
    _ensure_readers_registered()
    active_lang = get_active_language(lang_code)

    if isinstance(target, Page):
        chosen_path_str = pick_variant(target, active_lang)
        file_path = Path(chosen_path_str)
        base_page = target
    else:
        file_path = Path(target)
        base_page = None

    ext = file_path.suffix.lower()
    reader = READERS.get(ext)
    if reader is None:
        raise ValueError(f"Unsupported documentation file extension: {ext}")

    effective_node_dir = node_dir or file_path.parent
    rendered = reader(file_path, effective_node_dir, active_lang)

    if base_page is not None:
        rendered.slug = base_page.slug
        rendered.raw_stem = base_page.raw_stem
        rendered.languages = list(base_page.languages)
        rendered.variants = dict(base_page.variants)
    return rendered
