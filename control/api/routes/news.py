from __future__ import annotations

from fastapi import APIRouter

from news_feed.adapter import evaluate_news_status, list_news_events

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def list_resource() -> dict:
    return {"module": "news", "description": "News and fundamental analysis status", "mode": "production-required"}


@router.get("/status")
def news_status(symbol: str | None = None) -> dict:
    return evaluate_news_status(symbol)


@router.get("/events")
def news_events(symbol: str | None = None, limit: int = 50) -> dict:
    return list_news_events(symbol=symbol, limit=limit)

