"""JSON reader for AAD-docs."""
from __future__ import annotations

import json
from pathlib import Path

from aad_docs.discovery import strip_numeric_prefix
from aad_docs.nodes import Page


def read(file_path: Path, node_dir: Path | None = None, lang_code: str = "en") -> Page:
    """Parse a .json file and validate its type for the simulator or viewer."""
    raw = file_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("type") != "flow":
        raise ValueError(f"JSON file {file_path.name} must be an object with 'type': 'flow'")
    raw_stem = file_path.stem
    slug = strip_numeric_prefix(raw_stem)
    title = data.get("title") or slug
    return Page(
        slug=slug,
        title=title,
        kind="json",
        languages=[lang_code],
        variants={lang_code: str(file_path)},
        content=data,
        raw_stem=raw_stem,
        scripts=["aad_docs/simulator.js"],
    )
