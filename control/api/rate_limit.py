from __future__ import annotations

def rate_limit_key(user_id: str, route: str) -> str:
    return f"rate:{user_id}:{route}"
