"""Root node: documentation that crosses every app in this project."""
from aad_docs import Node

node = Node(
    slug="project",
    title="AAD-docs project",
    title_es="Proyecto AAD-docs",
    order=0,
    pages=[
        "00-map",
        "02-getting-started",
        "03-architecture",
        "08-operations",
        "HOW-DOCS-WORK",
        "PLAN",
    ],
)
