from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def list_resource() -> dict:
    return {"module": "news", "description": "News and fundamental analysis status", "mode": "production-required"}


@router.get("/status")
def news_status(symbol: str | None = None) -> dict:
    provider_enabled = os.getenv("NEWS_PROVIDER_ENABLED", "false").lower() == "true"
    high_impact_next_minutes = int(os.getenv("NEWS_HIGH_IMPACT_NEXT_MINUTES", "999"))
    halt_active = not provider_enabled or high_impact_next_minutes <= 45
    return {
        "symbol": symbol,
        "provider_enabled": provider_enabled,
        "high_impact_next_minutes": high_impact_next_minutes if provider_enabled else None,
        "news_halt_active": halt_active,
        "risk_status": "news_safe_mode" if halt_active else "news_clear",
        "note": "News-sensitive strategies remain blocked until an approved provider is enabled and fresh.",
    }

