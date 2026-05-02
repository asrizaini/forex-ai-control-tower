from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    account_ids: tuple[str, ...] = ()


def decode_token(token: str | None) -> Principal | None:
    if not token:
        return None
    if token == os.getenv("CONTROL_TOWER_TEST_TOKEN", "dev-test-token"):
        return Principal(user_id="test-user", role="super_admin", account_ids=("demo-account",))
    return None


def issue_mock_token(user_id: str) -> dict:
    return {
        "access_token": os.getenv("CONTROL_TOWER_TEST_TOKEN", "dev-test-token"),
        "refresh_token": "mock-refresh-token",
        "token_type": "bearer",
        "user_id": user_id,
    }
