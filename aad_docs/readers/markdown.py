"""
Markdown reader for AAD-docs.

Renders .md files to HTML with raw HTML disabled.
"""

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from aad_docs.nodes import Page
from aad_docs.readers import register_reader


# Configure markdown-it with safe settings
_md = MarkdownIt(
    "commonmark",
    {
        "html": False,  # Disable raw HTML
        "linkify": True,
        "typographer": True,
    },
)


def _extract_title(content: str) -> str:
    """Extract the first heading as the title."""
    lines = content.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = 0
            while stripped.startswith("#"):
                stripped = stripped[1:]
                level += 1
            return stripped.strip()
    return "Untitled"


def _extract_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter if present."""
    import re
    
    frontmatter = {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if match:
        import yaml
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            pass
        content = content[match.end():]
    
    return frontmatter, content


@register_reader(".md")
def read_md(file_path: str, lang_code: str = "en") -> Page:
    """
    Read and render a .md file.
    
    Args:
        file_path: Path to the .md file
        lang_code: Language code
    
    Returns:
        Page instance with rendered HTML content
    """
    from pathlib import Path
    
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    
    # Extract frontmatter
    frontmatter, content = _extract_frontmatter(content)
    
    # Extract title from first heading
    title = _extract_title(content)
    
    # Render markdown to HTML
    html_content = _md.render(content)
    
    # Remove the header if present (Django will add its own)
    if title:
        html_content = html_content.lstrip()
    
    # Determine slug from filename
    stem = path.stem
    # Remove numeric prefix if present (e.g., "01-overview" -> "overview")
    import re
    slug = re.sub(r"^\d+-", "", stem)
    
    return Page(
        slug=slug,
        title=title,
        kind="md",
        languages={lang_code: file_path},
        variants={lang_code: file_path},
        frontmatter=frontmatter,
        content=html_content,
    )
