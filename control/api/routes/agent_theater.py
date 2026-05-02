from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/agent-theater", tags=["agent-theater"])


@router.get("")
def list_resource() -> dict:
    return {"module": "agent_theater", "description": "Human-readable agent event summaries", "mode": "mock-safe"}
