REDACTED_KEYS = {"password", "token", "secret", "api_key", "broker_credentials"}


def redact(payload: dict) -> dict:
    safe = {}
    for key, value in payload.items():
        if any(marker in key.lower() for marker in REDACTED_KEYS):
            safe[key] = "[REDACTED]"
        else:
            safe[key] = value
    return safe
