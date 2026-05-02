from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["system"])


@router.get("")
def list_resource() -> dict:
    return {"module": "system", "description": "System health, environment, audit, deployment status", "mode": "production-required"}

