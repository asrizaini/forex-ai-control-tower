from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("")
def list_resource() -> dict:
    return {"module": "trades", "description": "Trade journal and execution state", "mode": "mock-safe"}
