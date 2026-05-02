from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
def list_resource() -> dict:
    return {"module": "signals", "description": "Signal review queue", "mode": "production-required"}

