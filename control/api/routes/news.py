from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def list_resource() -> dict:
    return {"module": "news", "description": "News and fundamental analysis status", "mode": "production-required"}

