from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/tuning", tags=["tuning"])


@router.get("")
def list_resource() -> dict:
    return {"module": "tuning", "description": "Strategy tuning jobs", "mode": "mock-safe"}
