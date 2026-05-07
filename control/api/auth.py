from __future__ import annotations

import base64
import hmac
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .credential_store import runtime_value

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    account_ids: tuple[str, ...] = ()


def _secret() -> bytes | None:
    value = runtime_value("JWT_SECRET_KEY")
    return value.encode() if value else None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode())


def decode_token(token: str | None) -> Principal | None:
    secret = _secret()
    if not token or not secret or "." not in token:
        return None
    payload_raw, signature = token.rsplit(".", 1)
    expected = hmac.new(secret, payload_raw.encode(), sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        payload: dict[str, Any] = json.loads(_unb64url(payload_raw))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    account_ids = tuple(str(item) for item in payload.get("account_ids", ()))
    return Principal(user_id=str(payload["sub"]), role=str(payload["role"]), account_ids=account_ids)


def issue_token(user_id: str, role: str, account_ids: tuple[str, ...] = (), ttl_seconds: int = 900) -> dict:
    secret = _secret()
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is required to issue tokens")
    payload = {
        "sub": user_id,
        "role": role,
        "account_ids": list(account_ids),
        "exp": int(time.time()) + ttl_seconds,
    }
    payload_raw = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret, payload_raw.encode(), sha256).hexdigest()
    return {
        "access_token": f"{payload_raw}.{signature}",
        "token_type": "bearer",
        "expires_in": ttl_seconds,
    }
