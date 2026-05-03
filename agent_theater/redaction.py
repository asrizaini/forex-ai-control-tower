REDACTED_KEYS = {"password", "token", "secret", "api_key", "broker_credentials"}


def redact(payload: object) -> object:
    if isinstance(payload, dict):
        safe = {}
        for key, value in payload.items():
            if any(marker in key.lower() for marker in REDACTED_KEYS):
                safe[key] = "[REDACTED]"
            else:
                safe[key] = redact(value)
        return safe
    if isinstance(payload, list):
        return [redact(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(redact(item) for item in payload)
    return payload
