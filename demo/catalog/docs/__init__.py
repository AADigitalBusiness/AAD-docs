"""Catalog app documentation node."""

from aad_docs import Node


node = Node(
    slug="catalog",
    title="Product Catalog",
    title_es="Cat\u00e1logo de Productos",
    order=20,
    pages=[
        "01-overview",
        "02-models",
        "03-usage",
    ],
)
