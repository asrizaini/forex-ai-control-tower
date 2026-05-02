from __future__ import annotations

from .locale_manager import DO_NOT_TRANSLATE, normalize_language
from .templates import TEMPLATES


def translate_template(key: str, language: str = "en") -> str:
    normalized = normalize_language(language)
    if normalized == "auto":
        normalized = "en"
    return TEMPLATES.get(key, {}).get(normalized, TEMPLATES.get(key, {}).get("en", key))


def preserve_canonical_terms(text: str) -> bool:
    return all(term in text for term in DO_NOT_TRANSLATE if term in text)
