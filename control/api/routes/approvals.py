from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_resource() -> dict:
    return {"module": "approvals", "description": "Manual approval workflow", "mode": "production-required"}

