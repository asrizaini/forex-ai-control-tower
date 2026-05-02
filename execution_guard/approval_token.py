from __future__ import annotations

import hmac
import os
import time
from hashlib import sha256


def create_approval_token(account_id: str, strategy_id: str, ttl_seconds: int = 60) -> str:
    secret = os.getenv("EXECUTION_GUARD_SIGNING_KEY", "dev-only-nonsecret-signing-key")
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{account_id}:{strategy_id}:{expires_at}"
    signature = hmac.new(secret.encode(), payload.encode(), sha256).hexdigest()
    return f"{payload}:{signature}"


def validate_approval_token(token: str | None) -> bool:
    if not token:
        return False
    parts = token.split(":")
    if len(parts) != 4:
        return False
    account_id, strategy_id, expires_raw, signature = parts
    try:
        expires_at = int(expires_raw)
    except ValueError:
        return False
    if expires_at < int(time.time()):
        return False
    expected = create_approval_token(account_id, strategy_id, expires_at - int(time.time())).rsplit(":", 1)[1]
    return hmac.compare_digest(expected, signature)
