"""YAML reader for AAD-docs."""
from __future__ import annotations

from pathlib import Path

import yaml

from aad_docs.discovery import strip_numeric_prefix
from aad_docs.nodes import Page


def read(file_path: Path, node_dir: Path | None = None, lang_code: str = "en") -> Page:
    """Parse a .yml file into data for the explorer."""
    raw = file_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    raw_stem = file_path.stem
    slug = strip_numeric_prefix(raw_stem)
    return Page(
        slug=slug,
        title=slug,
        kind="yml",
        languages=[lang_code],
        variants={lang_code: str(file_path)},
        content=data,
        raw_stem=raw_stem,
        scripts=["aad_docs/explorer.js"],
    )
