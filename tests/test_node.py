"""
Test Node import without Django setup.

This test verifies that `from aad_docs import Node` works before Django is ready,
as required by the architecture.
"""


def test_node_import_without_django():
    """Test that Node can be imported without Django."""
    # Clear any Django modules that might be loaded
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("django"):
            del sys.modules[mod]
    
    # Remove Django from path temporarily
    import os
    django_path = None
    for path in sys.path:
        if "django" in path.lower() and "site-packages" in path:
            django_path = path
            break
    
    if django_path:
        sys.path.remove(django_path)
    
    # This should work even without Django
    from aad_docs import Node
    
    # Create a node
    node = Node(
        slug="test",
        title="Test Node",
        order=10,
    )
    
    assert node.slug == "test"
    assert node.title == "Test Node"
    assert node.order == 10
    assert node.children == []
    assert node.pages == []
