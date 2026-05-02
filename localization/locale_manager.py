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
