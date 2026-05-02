from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("")
def list_resource() -> dict:
    return {"module": "mobile", "description": "Mobile bootstrap and push registration", "mode": "mock-safe"}


@router.get("/bootstrap")
def bootstrap() -> dict:
    return {"environment": "demo", "trading_mode": "monitor_only", "language_modes": ["en", "ms-MY", "auto"]}


@router.post("/push/register")
def register_push(payload: dict) -> dict:
    return {"registered": True, "provider": payload.get("provider", "fcm"), "secret_stored": False}
