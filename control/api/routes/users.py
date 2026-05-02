from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_resource() -> dict:
    return {"module": "users", "description": "User management uses deny-by-default RBAC", "mode": "mock-safe"}
