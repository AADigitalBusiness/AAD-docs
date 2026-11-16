"""
Node and Page data classes for AAD-docs.

These are pure Python data classes with no Django dependencies.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Page:
    """Represents a single documentation page file."""
    
    slug: str
    title: str
    kind: str  # "md", "mdx", "yml", "csv", "json"
    languages: dict[str, str]  # {lang_code: variant_filename}
    variants: dict[str, str]  # {lang_code: file_path}
    frontmatter: dict[str, Any] = field(default_factory=dict)
    content: str | dict | list = ""


@dataclass
class Node:
    """
    Represents a documentation folder (app or section).
    
    This is the owner of node-options.csv and the primary data structure
    passed between components.
    
    Attributes:
        slug: URL segment for this node (e.g., "orders" -> /docs/orders/)
        title: Display title in the active language
        title_es: Spanish title (if available)
        order: Position among siblings (lower = earlier)
        pages: List of page slugs to show (empty = show all)
        visible: Callable to filter pages (None = all visible)
        children: List of child Node instances
    """
    
    slug: str
    title: str
    title_es: str | None = None
    order: int = 0
    pages: list[str] = field(default_factory=list)
    visible: Any = None  # Callable[[request, page_name], bool] | None
    children: list["Node"] = field(default_factory=list)
    
    def __post_init__(self):
        """Ensure children is a list."""
        if self.children is None:
            self.children = []
        if self.pages is None:
            self.pages = []
