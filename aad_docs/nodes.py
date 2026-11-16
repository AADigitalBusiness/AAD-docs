"""Node and Page data classes for AAD-docs.

Pure Python module with no Django imports. Owner of node-options.csv.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


NODE_OPTIONS_SPEC: tuple[dict[str, str], ...] = (
    {
        "option": "slug",
        "type": "str",
        "required": "no",
        "default": "App label with underscores as hyphens; folder name for a child node",
        "meaning": "Address segment of the node: /docs/<slug>/. Does not have to match the app name.",
    },
    {
        "option": "title",
        "type": "str",
        "required": "no",
        "default": "verbose_name of the app; folder name without its numeric prefix for a child node",
        "meaning": "Name shown in the menu.",
    },
    {
        "option": "title_es",
        "type": "str",
        "required": "no",
        "default": "Value of title",
        "meaning": "Name shown in the menu when Spanish is active.",
    },
    {
        "option": "order",
        "type": "int",
        "required": "no",
        "default": "100",
        "meaning": "Position among sibling nodes. Lower comes first. Ties sort by slug.",
    },
    {
        "option": "pages",
        "type": "list of str",
        "required": "no",
        "default": "Every readable file and child node, sorted by name",
        "meaning": "Pages and child nodes to show, in order, named by file stem or folder name. A name left out is hidden.",
    },
    {
        "option": "visible",
        "type": "callable",
        "required": "no",
        "default": "Always visible",
        "meaning": "Function that receives the request and a page name and returns whether to show it. It filters the menu and the access to the page. Use it to hide a page by permission.",
    },
)


@dataclass
class Page:
    """One file inside a node. Holds slug, title, kind, languages, variants, frontmatter and content."""

    slug: str
    title: str
    kind: str
    languages: list[str] = field(default_factory=list)
    variants: dict[str, str] = field(default_factory=dict)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    content: Any = ""
    raw_stem: str = ""
    scripts: list[str] = field(default_factory=list)


@dataclass
class Node:
    """One documentation folder. Holds slug, titles, order, pages, visible and children. Owner of node-options.csv."""

    slug: str | None = None
    title: str | None = None
    title_es: str | None = None
    order: int = 100
    pages: list[str] | None = None
    visible: Callable[..., bool] | None = None
    children: list["Node"] = field(default_factory=list)
    page_items: list[Page] = field(default_factory=list)
    path: Path | None = None
    app_label: str | None = None
    raw_name: str = ""

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []
        if self.page_items is None:
            self.page_items = []
        if self.title and not self.title_es:
            self.title_es = self.title

    def title_for(self, lang: str = "en") -> str:
        """Return the localized title for the node."""
        if lang.startswith("es") and self.title_es:
            return self.title_es
        return self.title or self.slug or ""
