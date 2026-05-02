from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


@router.get("")
def list_resource() -> dict:
    return {"module": "openclaw", "description": "Optional OpenClaw gateway, disabled by default", "mode": "mock-safe"}
