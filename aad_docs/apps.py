"""
AAD-docs app configuration.

Registers the app and its Django system checks.
"""

from django.apps import AppConfig
from django.core.checks import Error, register


class AadDocsConfig(AppConfig):
    """AAD-docs Django app configuration."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "aad_docs"
    verbose_name = "AAD-docs"


@register()
def check_docs_folders(app_configs, **kwargs):
    """
    System check: verify that docs/ folders have __init__.py files.
    
    This is a Django system check that runs with `python manage.py check`.
    """
    from aad_docs.discovery import find_doc_dirs
    
    errors = []
    
    try:
        doc_dirs = find_doc_dirs()
        for doc_dir in doc_dirs:
            init_path = doc_dir / "__init__.py"
            if not init_path.exists():
                errors.append(
                    Error(
                        f"Documentation folder {doc_dir} is missing __init__.py",
                        id="aad_docs.E001",
                    )
                )
    except Exception as e:
        errors.append(
            Error(
                f"Error checking docs folders: {e}",
                id="aad_docs.E002",
            )
        )
    
    return errors
