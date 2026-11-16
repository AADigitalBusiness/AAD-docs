"""Language selection and variant fallback for AAD-docs."""
from __future__ import annotations

from aad_docs.conf import get_settings
from aad_docs.nodes import Page


def get_active_language(lang_code: str | None = None) -> str:
    """Return the normalized active language code against AAD_DOCS['LANGUAGES']."""
    cfg = get_settings()
    languages: list[str] = list(cfg.get("LANGUAGES") or ["en", "es"])
    default_lang = languages[0] if languages else "en"

    if not lang_code:
        try:
            from django.utils import translation

            lang_code = translation.get_language()
        except Exception:
            lang_code = None

    if not lang_code:
        lang_code = default_lang

    norm = lang_code.lower().replace("_", "-")
    if norm in languages:
        return norm
    short = norm.split("-")[0]
    if short in languages:
        return short
    return default_lang


def pick_variant(page: Page, lang_code: str | None = None) -> str:
    """Normalize the active language against LANGUAGES and return that variant of a page, else the first language."""
    cfg = get_settings()
    languages: list[str] = list(cfg.get("LANGUAGES") or ["en", "es"])
    default_lang = languages[0] if languages else "en"
    active = get_active_language(lang_code)

    if active in page.variants:
        return page.variants[active]
    if default_lang in page.variants:
        return page.variants[default_lang]
    if page.variants:
        return next(iter(page.variants.values()))
    return ""
