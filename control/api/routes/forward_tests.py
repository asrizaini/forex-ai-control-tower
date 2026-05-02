from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/forward-tests", tags=["forward-tests"])


@router.get("")
def list_resource() -> dict:
    return {"module": "forward_tests", "description": "Forward test jobs and results", "mode": "production-required"}

