"""
Discovery module for AAD-docs.

Walks INSTALLED_APPS and the root folder to find docs/ directories.
"""

import importlib
from pathlib import Path
from typing import Any

from django.apps import apps

from aad_docs.conf import get_settings
from aad_docs.nodes import Node


def find_doc_dirs() -> list[Path]:
    """
    Find all docs/ directories that have an __init__.py file.
    
    Walks through INSTALLED_APPS and the project root folder.
    
    Returns:
        List of Path objects pointing to valid docs/ directories.
    """
    settings = get_settings()
    doc_dirs: list[Path] = []
    
    # Check each installed app
    for app_config in apps.get_app_configs():
        app_path = Path(app_config.path)
        doc_path = app_path / "docs"
        
        if doc_path.exists() and doc_path.is_dir():
            init_path = doc_path / "__init__.py"
            if init_path.exists():
                doc_dirs.append(doc_path)
    
    # Check project root if ROOT is set
    if settings.get("ROOT"):
        root_path = Path(settings["ROOT"])
        if root_path.exists() and root_path.is_dir():
            # Verify it has __init__.py
            init_path = root_path / "__init__.py"
            if init_path.exists():
                doc_dirs.append(root_path)
    
    # Also check for a docs/ folder in the project root
    # (where this repository's docs live)
    project_root = Path.cwd()
    project_docs = project_root / "docs"
    if project_docs.exists() and project_docs.is_dir():
        init_path = project_docs / "__init__.py"
        if init_path.exists() and project_docs not in doc_dirs:
            doc_dirs.append(project_docs)
    
    return doc_dirs


def resolve_node(doc_path: Path) -> Node | None:
    """
    Load a docs package by file path under a unique module name.
    
    Reads the node attribute from __init__.py and applies defaults.
    
    Args:
        doc_path: Path to the docs/ directory
    
    Returns:
        Node instance or None if loading fails
    """
    import sys
    
    init_path = doc_path / "__init__.py"
    if not init_path.exists():
        return None
    
    # Create a unique module name based on the path
    # This avoids collisions with any existing module named "docs"
    module_name = f"_aad_docs_node_{hash(str(doc_path.resolve()))}"
    
    try:
        # Add the parent directory to sys.path temporarily
        parent_path = str(doc_path.parent)
        if parent_path not in sys.path:
            sys.path.insert(0, parent_path)
        
        # Import the module by path
        spec = importlib.util.spec_from_file_location(module_name, str(init_path))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get the node from the module
            if hasattr(module, "node") and isinstance(module.node, Node):
                return module.node
            
            # If no node defined, create a default one from folder name
            folder_name = doc_path.name
            return Node(
                slug=folder_name.replace("_", "-"),
                title=folder_name.replace("_", " ").title(),
                order=0,
            )
        
    except Exception as e:
        # Log the error but don't crash - node will be skipped
        # In production, docs_check will report this (D003)
        pass
    finally:
        # Clean up sys.path
        if parent_path in sys.path:
            sys.path.remove(parent_path)
        # Remove the temporary module
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    return None


def build_tree() -> Node:
    """
    Build and cache the full node tree from discovered docs/ directories.
    
    Returns:
        Root Node containing all discovered documentation nodes.
    """
    from django.core.cache import cache
    
    settings = get_settings()
    cache_key = "aad_docs_node_tree"
    
    # Check cache (disabled in DEBUG mode)
    if not settings.get("DEBUG") and settings.get("CACHE_TIMEOUT") is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    # Find all doc directories
    doc_dirs = find_doc_dirs()
    
    # Root node
    root = Node(
        slug="root",
        title="Documentation",
        title_es="Documentaci\u00f3n",
        order=-100,  # Always first
    )
    
    # Resolve each doc directory to a node
    for doc_path in doc_dirs:
        node = resolve_node(doc_path)
        if node:
            # Sort children by order
            root.children.append(node)
    
    # Sort children by order, then by slug
    root.children.sort(key=lambda n: (n.order, n.slug))
    
    # Cache the result
    if settings.get("CACHE_TIMEOUT") is not None:
        cache.set(cache_key, root, settings["CACHE_TIMEOUT"])
    
    return root
