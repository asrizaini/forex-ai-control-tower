from __future__ import annotations

from fastapi import APIRouter
from ..auth import issue_mock_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("")
def list_resource() -> dict:
    return {"module": "auth", "description": "Authentication and token lifecycle", "mode": "mock-safe"}


@router.post("/login")
def login(payload: dict) -> dict:
    user_id = str(payload.get("user_id", "demo-user"))
    return issue_mock_token(user_id)
