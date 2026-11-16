"""
Smoke tests for AAD-docs M1a milestone.

These tests verify the acceptance criteria for M1a.
"""

import pytest


class TestNodeImport:
    """Test that Node can be imported without Django."""
    
    def test_node_import(self):
        """Test Node import and instantiation."""
        from aad_docs import Node
        
        node = Node(
            slug="test-app",
            title="Test Application",
            order=10,
        )
        
        assert node.slug == "test-app"
        assert node.title == "Test Application"
        assert node.order == 10
        assert node.children == []
    
    def test_node_with_es(self):
        """Test Node with Spanish title."""
        from aad_docs import Node
        
        node = Node(
            slug="test-app",
            title="Test Application",
            title_es="Aplicaci\u00f3n de Prueba",
            order=10,
        )
        
        assert node.title_es == "Aplicaci\u00f3n de Prueba"


class TestDocsUrlImport:
    """Test that docs_url can be imported."""
    
    def test_docs_url_importable(self):
        """Test docs_url is importable."""
        from aad_docs import docs_url
        
        assert callable(docs_url)


class TestConf:
    """Test configuration."""
    
    def test_defaults_exist(self):
        """Test DEFAULTS exist."""
        from aad_docs.conf import DEFAULTS
        
        assert "ROOT" in DEFAULTS
        assert "ACCESS" in DEFAULTS
        assert "SHOW_TREE" in DEFAULTS
    
    def test_get_settings_works(self):
        """Test get_settings returns dict (without Django configured)."""
        from aad_docs.conf import get_settings, DEFAULTS
        
        settings = get_settings()
        assert isinstance(settings, dict)
        # Without Django, should return only defaults
        assert settings == DEFAULTS


class TestAppConfig:
    """Test app configuration."""
    
    def test_app_config_exists(self):
        """Test AadDocsConfig exists."""
        from aad_docs.apps import AadDocsConfig
        
        assert AadDocsConfig.name == "aad_docs"
        assert AadDocsConfig.verbose_name == "AAD-docs"
