"""App node: the documentation of aad_docs itself."""
from aad_docs import Node

node = Node(
    slug="aad-docs",
    title="AAD-docs",
    title_es="AAD-docs",
    order=10,
    pages=[
        "01-overview",
        "04-read-the-code",
        "code-map",
        "request-flow",
        "05-guides",
        "06-reference",
        "07-decisions",
    ],
)
