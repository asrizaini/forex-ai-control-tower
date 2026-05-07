from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from datetime import datetime, timedelta

from .time_utils import utcnow


PASSWORD_ITERATIONS = 210_000


def random_token_urlsafe(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def password_hash(password: str, salt: str | None = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PASSWORD_ITERATIONS)
    return base64.b64encode(digest).decode(), salt


def verify_password(password: str, expected_hash: str, salt: str) -> bool:
    digest, _salt = password_hash(password, salt)
    return hmac.compare_digest(digest, expected_hash)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _totp_code(secret: str, timestep: int) -> str:
    padding = "=" * (-len(secret) % 8)
    key = base64.b32decode((secret + padding).upper())
    msg = struct.pack(">Q", timestep)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code:06d}"


def verify_totp(secret: str | None, code: str | None, window: int = 1) -> bool:
    if not secret or not code or not code.isdigit():
        return False
    current = int(time.time() // 30)
    return any(hmac.compare_digest(_totp_code(secret, current + offset), code) for offset in range(-window, window + 1))


def refresh_expiry(days: int = 7) -> datetime:
    return utcnow() + timedelta(days=days)


def otpauth_uri(user_id: str, secret: str) -> str:
    issuer = os.getenv("TOTP_ISSUER", "Forex AI Control Tower")
    return f"otpauth://totp/{issuer}:{user_id}?secret={secret}&issuer={issuer}&digits=6&period=30"

