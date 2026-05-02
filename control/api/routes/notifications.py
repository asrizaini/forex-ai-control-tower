from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_resource() -> dict:
    return {"module": "notifications", "description": "Notification preferences and routing", "mode": "mock-safe"}
