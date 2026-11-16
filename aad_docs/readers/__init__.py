"""
Readers module for AAD-docs.

Registry of file extensions and their readers.
This module is the owner of file-types.csv.
"""

from typing import Callable

from aad_docs.nodes import Page

# Registry mapping extensions to reader functions
READERS: dict[str, Callable[[str, str], Page]] = {}


def register_reader(extension: str) -> Callable:
    """Decorator to register a reader for a file extension."""
    def decorator(func: Callable[[str, str], Page]) -> Callable:
        READERS[extension] = func
        return func
    return decorator


def read_page(file_path: str, lang_code: str = "en") -> Page:
    """
    Pick the reader for a file extension and return a Page.
    
    Args:
        file_path: Path to the file
        lang_code: Language code for the page
    
    Returns:
        Page instance with content
    """
    import os
    from pathlib import Path
    
    path = Path(file_path)
    ext = path.suffix.lower()
    
    # Handle .mdx as .md for now (simplified)
    if ext == ".mdx":
        ext = ".md"
    
    reader = READERS.get(ext)
    if reader is None:
        # Unknown extension - create empty page
        return Page(
            slug=path.stem,
            title=path.stem.replace("-", " "),
            kind=ext.lstrip("."),
            languages={lang_code: file_path},
            variants={lang_code: file_path},
            content="",
        )
    
    return reader(file_path, lang_code)
