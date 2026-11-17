"""Pytest configuration and shared fixtures for AAD-docs tests."""
from __future__ import annotations

import pytest

from aad_docs.discovery import clear_tree_cache


@pytest.fixture(autouse=True)
def _reset_tree_cache() -> None:
    clear_tree_cache()
    yield
    clear_tree_cache()
