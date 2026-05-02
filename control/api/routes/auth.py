from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from ..auth import issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("")
def list_resource() -> dict:
    return {"module": "auth", "description": "Authentication and token lifecycle", "mode": "production-required"}


@router.post("/login")
def login(payload: dict) -> dict:
    if os.getenv("LOCAL_AUTH_BOOTSTRAP_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Production identity provider is not configured")
    user_id = str(payload.get("user_id", ""))
    role = str(payload.get("role", "viewer"))
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return issue_token(user_id=user_id, role=role, account_ids=tuple(payload.get("account_ids", ())))

