"""
Language handling for AAD-docs.

Normalizes language codes and picks the appropriate variant.
"""

from django.conf import settings as django_settings


def pick_variant(page: "Page", lang_code: str | None = None) -> str:
    """
    Normalize the active language against LANGUAGES and return that variant.
    
    Args:
        page: The Page to pick a variant from
        lang_code: The requested language code (defaults to active Django language)
    
    Returns:
        The file path for the best matching variant
    """
    if lang_code is None:
        # Get active Django language
        if hasattr(django_settings, "LANGUAGE_CODE"):
            lang_code = django_settings.LANGUAGE_CODE
        else:
            lang_code = "en"
    
    # Normalize the language code
    # e.g., "es-co" -> "es", "en-us" -> "en"
    if "-" in lang_code:
        lang_code = lang_code.split("-")[0]
    
    # Check if we have this language
    if lang_code in page.variants:
        return page.variants[lang_code]
    
    # Fall back to first available language
    if page.variants:
        return next(iter(page.variants.values()))
    
    # No variants available
    return ""
