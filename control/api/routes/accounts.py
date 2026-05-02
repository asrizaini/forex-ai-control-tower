from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_resource() -> dict:
    return {"module": "accounts", "description": "Account isolation and account-group management", "mode": "production-required"}

