from __future__ import annotations

import json
from pathlib import Path

SUPPORTED_LANGUAGES = ("en", "ms-MY", "auto")
DEFAULT_LANGUAGE = "en"
INTERNAL_LANGUAGE = "en"
DO_NOT_TRANSLATE = {
    "MT5",
    "API",
    "strategy_id",
    "account_id",
    "EURUSD",
    "GBPUSD",
    "XAUUSD",
    "USDJPY",
}


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def locale_root() -> Path:
    return Path(__file__).resolve().parent.parent / "locales"


def load_locale(language: str = "en", namespace: str = "common") -> dict:
    normalized = normalize_language(language)
    if normalized == "auto":
        normalized = DEFAULT_LANGUAGE
    path = locale_root() / normalized / f"{namespace}.json"
    fallback = locale_root() / DEFAULT_LANGUAGE / f"{namespace}.json"
    target = path if path.exists() else fallback
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def translate_key(namespace: str, key: str, language: str = "en") -> str:
    locale = load_locale(language, namespace)
    return str(locale.get(key, load_locale(DEFAULT_LANGUAGE, namespace).get(key, key)))
