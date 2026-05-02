from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/localization", tags=["localization"])


@router.get("")
def list_resource() -> dict:
    return {"module": "localization", "description": "Language and locale support", "mode": "production-required"}

