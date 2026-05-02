from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("")
def list_resource() -> dict:
    return {"module": "backtests", "description": "Backtest jobs and results", "mode": "mock-safe"}
