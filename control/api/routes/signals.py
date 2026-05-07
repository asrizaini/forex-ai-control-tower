from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from ..models import SignalRecord
from ..db import get_db

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
def list_resource() -> dict:
    return {"module": "signals", "description": "Signal review queue", "mode": "production-required"}


@router.get("/summary")
def signals_summary(db: Session = Depends(get_db)) -> dict:
    """Return signal summary grouped by symbol with latest signal per pair."""
    rows = list(
        db.scalars(
            select(SignalRecord)
            .order_by(desc(SignalRecord.created_at))
            .limit(200)
        )
    )
    seen: dict[str, SignalRecord] = {}
    for row in rows:
        key = f"{row.symbol}|{row.timeframe}"
        if key not in seen:
            seen[key] = row

    items = []
    summary: dict[str, list[str]] = {
        "no_valid_signal": [],
        "blocked": [],
        "stale": [],
        "missing_data": [],
    }
    for key, row in seen.items():
        item = {
            "pair": row.symbol,
            "timeframe": row.timeframe,
            "direction": row.direction,
            "confidence": round(row.confidence, 1),
            "signal_status": row.signal_status,
            "freshness_status": row.freshness_status,
            "strategy_id": row.strategy_id,
            "reason": row.reason,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
        }
        items.append(item)
        bucket = row.signal_status if row.signal_status in summary else None
        freshness_bucket = row.freshness_status if row.freshness_status in summary else None
        if bucket:
            summary[bucket].append(row.symbol)
        if freshness_bucket and freshness_bucket != bucket:
            summary.setdefault(freshness_bucket, []).append(row.symbol)

    return {"items": items, "summary": summary}


@router.get("/records")
def signals_records(
    limit: int = Query(default=100, ge=1, le=1000),
    symbol: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Return raw signal records for dashboard display."""
    query = select(SignalRecord)
    if symbol:
        query = query.where(SignalRecord.symbol == symbol.upper())
    rows = list(db.scalars(query.order_by(desc(SignalRecord.created_at)).limit(limit)))
    return {
        "items": [
            {
                "signal_id": row.signal_id,
                "pair": row.symbol,
                "timeframe": row.timeframe,
                "direction": row.direction,
                "confidence": round(row.confidence, 1),
                "signal_status": row.signal_status,
                "freshness_status": row.freshness_status,
                "strategy_id": row.strategy_id,
                "entry_idea": row.entry_idea,
                "stop_loss_idea": row.stop_loss_idea,
                "take_profit_idea": row.take_profit_idea,
                "reason": row.reason,
                "blockers": row.blockers,
                "risk_notes": row.risk_notes,
                "timestamp": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }

