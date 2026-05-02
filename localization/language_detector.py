def detect_language(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("akaun", "risiko", "dagangan", "kelulusan")):
        return "ms-MY"
    return "en"
