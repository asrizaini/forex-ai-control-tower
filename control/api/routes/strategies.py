from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("")
def list_resource() -> dict:
    return {"module": "strategies", "description": "Strategy registry and lifecycle governance", "mode": "production-required"}

