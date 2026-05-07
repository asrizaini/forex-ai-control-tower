from __future__ import annotations

import hmac
import os
import time
from hashlib import sha256


def _sign_payload(secret: str, payload: str) -> str:
    """Compute HMAC-SHA256 signature for a given payload string."""
    return hmac.new(secret.encode(), payload.encode(), sha256).hexdigest()


def create_approval_token(account_id: str, strategy_id: str, ttl_seconds: int = 60) -> str:
    secret = os.getenv("EXECUTION_GUARD_SIGNING_KEY")
    if not secret:
        raise RuntimeError("EXECUTION_GUARD_SIGNING_KEY is required")
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{account_id}:{strategy_id}:{expires_at}"
    signature = _sign_payload(secret, payload)
    return f"{payload}:{signature}"


def validate_approval_token(token: str | None) -> bool:
    secret = os.getenv("EXECUTION_GUARD_SIGNING_KEY")
    if not secret:
        return False
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
    # Recompute the signature from the exact same payload to avoid
    # time-of-check vs time-of-use drift that occurred when calling
    # create_approval_token() with a recomputed TTL.
    payload = f"{account_id}:{strategy_id}:{expires_raw}"
    expected = _sign_payload(secret, payload)
    return hmac.compare_digest(expected, signature)
