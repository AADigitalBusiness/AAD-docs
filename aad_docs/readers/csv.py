"""CSV reader for AAD-docs."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from aad_docs.discovery import strip_numeric_prefix
from aad_docs.nodes import Page


def read(file_path: Path, node_dir: Path | None = None, lang_code: str = "en") -> Page:
    """Parse a .csv file into columns and rows for the table."""
    raw = file_path.read_text(encoding="utf-8")
    rows = list(csv.reader(io.StringIO(raw)))
    columns = rows[0] if rows else []
    body_rows = rows[1:] if len(rows) > 1 else []
    raw_stem = file_path.stem
    slug = strip_numeric_prefix(raw_stem)
    return Page(
        slug=slug,
        title=slug,
        kind="csv",
        languages=[lang_code],
        variants={lang_code: str(file_path)},
        content={"columns": columns, "rows": body_rows},
        raw_stem=raw_stem,
        scripts=["aad_docs/table.js"],
    )
