from __future__ import annotations

import os
from ipaddress import ip_address, ip_network
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from ..control_schemas import AccountSnapshotOut, HistoricalCandleOut, MarketSnapshotOut, WorkerTelemetryIn
from ..db import get_db
from ..models import AccountSnapshot, HistoricalCandle, MarketSnapshot
from market_data_quality.analysis import multi_timeframe_summary, price_action_summary, spread_slippage_summary

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

PRIVATE_TELEMETRY_NETWORKS = (
    ip_network("10.10.1.0/24"),
    ip_network("127.0.0.0/8"),
)


@router.get("")
def list_resource() -> dict:
    return {
        "module": "telemetry",
        "description": "Persistent market/account snapshots from workers",
        "mode": "monitor-only-production",
    }


def _ingest_allowed(request: Request, x_telemetry_token: str | None) -> bool:
    expected = os.getenv("TELEMETRY_INGEST_TOKEN")
    if expected:
        return bool(x_telemetry_token) and x_telemetry_token == expected
    client_host = request.client.host if request.client else ""
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    return any(client_ip in network for network in PRIVATE_TELEMETRY_NETWORKS)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _datetime_or_now(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            return datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _persist_historical_candles(db: Session, symbol: str, item: dict[str, Any]) -> int:
    rates = item.get("rates") or item.get("candles") or []
    if not isinstance(rates, list):
        return 0
    timeframe = str(item.get("timeframe", "M1"))
    count = 0
    for rate in rates[-500:]:
        if not isinstance(rate, dict):
            continue
        db.add(
            HistoricalCandle(
                symbol=symbol,
                timeframe=timeframe,
                candle_time=_datetime_or_now(rate.get("time") or rate.get("timestamp")),
                open=_float_or_none(rate.get("open")),
                high=_float_or_none(rate.get("high")),
                low=_float_or_none(rate.get("low")),
                close=_float_or_none(rate.get("close")),
                tick_volume=_float_or_none(rate.get("tick_volume") or rate.get("volume")),
                spread=_float_or_none(rate.get("spread") or item.get("spread")),
                payload_json=rate,
            )
        )
        count += 1
    return count


def _persist_market_snapshots(db: Session, worker: str, result: dict[str, Any]) -> tuple[int, int]:
    snapshots = result.get("snapshots", [])
    if not isinstance(snapshots, list):
        return 0, 0
    count = 0
    candle_count = 0
    for item in snapshots:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        db.add(
            MarketSnapshot(
                worker=worker,
                symbol=symbol,
                trend=str(item.get("trend", "unknown")),
                spread=_float_or_none(item.get("spread")),
                freshness_seconds=_int_or_none(item.get("freshness_seconds")),
                rates_count=int(item.get("rates_count") or 0),
                feed_fresh=bool(item.get("feed_fresh", False)),
                data_quality=str(result.get("data_quality", "limited")),
                payload_json=item,
            )
        )
        count += 1
        candle_count += _persist_historical_candles(db, symbol, item)
    return count, candle_count


def _persist_account_snapshot(db: Session, worker: str, result: dict[str, Any]) -> int:
    account = result.get("account", {})
    if not isinstance(account, dict) or not account:
        return 0
    db.add(
        AccountSnapshot(
            worker=worker,
            login_masked=str(account.get("login_masked", "***")),
            server=str(account.get("server", "unknown")),
            currency=str(account.get("currency", "unknown")),
            balance=_float_or_none(account.get("balance")),
            equity=_float_or_none(account.get("equity")),
            margin_free=_float_or_none(account.get("margin_free")),
            drawdown_pct=_float_or_none(account.get("drawdown_pct")),
            positions_count=int(result.get("positions_count") or 0),
            trade_allowed=_bool_or_none(account.get("trade_allowed")),
            risk_mode=str(result.get("risk_mode", "monitor_only")),
            auto_execution_enabled=bool(result.get("auto_execution_enabled", False)),
            payload_json={"account": account, "positions_count": result.get("positions_count", 0)},
        )
    )
    return 1


@router.post("/worker-snapshot", status_code=status.HTTP_202_ACCEPTED)
def ingest_worker_snapshot(
    payload: WorkerTelemetryIn,
    request: Request,
    x_telemetry_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not _ingest_allowed(request, x_telemetry_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telemetry ingest is restricted")
    worker = payload.worker
    result = payload.result
    market_count, candle_count = _persist_market_snapshots(db, worker, result) if worker == "market" else (0, 0)
    account_count = _persist_account_snapshot(db, worker, result) if worker == "strategy_risk" else 0
    db.commit()
    return {"accepted": True, "market_snapshots": market_count, "historical_candles": candle_count, "account_snapshots": account_count}


@router.get("/market/latest", response_model=list[MarketSnapshotOut])
def latest_market_snapshots(symbol: str | None = None, limit: int = 50, db: Session = Depends(get_db)) -> list[MarketSnapshot]:
    query = select(MarketSnapshot).order_by(MarketSnapshot.created_at.desc()).limit(max(1, min(limit, 200)))
    if symbol:
        query = select(MarketSnapshot).where(MarketSnapshot.symbol == symbol.upper()).order_by(MarketSnapshot.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query))


@router.get("/market/candles", response_model=list[HistoricalCandleOut])
def historical_candles(symbol: str, timeframe: str = "M1", limit: int = 500, db: Session = Depends(get_db)) -> list[HistoricalCandle]:
    return list(
        db.scalars(
            select(HistoricalCandle)
            .where(HistoricalCandle.symbol == symbol.upper(), HistoricalCandle.timeframe == timeframe)
            .order_by(HistoricalCandle.candle_time.desc())
            .limit(max(1, min(limit, 5000)))
        )
    )


@router.get("/accounts/latest", response_model=list[AccountSnapshotOut])
def latest_account_snapshots(limit: int = 50, db: Session = Depends(get_db)) -> list[AccountSnapshot]:
    query = select(AccountSnapshot).order_by(AccountSnapshot.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query))


@router.get("/market/{symbol}/analysis")
def market_analysis(symbol: str, limit: int = 20, db: Session = Depends(get_db)) -> dict:
    snapshots = list(
        db.scalars(
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol == symbol.upper())
            .order_by(MarketSnapshot.created_at.desc())
            .limit(max(1, min(limit, 100)))
        )
    )
    payloads = [
        {
            **(snapshot.payload_json or {}),
            "trend": snapshot.trend,
            "spread": snapshot.spread,
            "feed_fresh": snapshot.feed_fresh,
            "rates_count": snapshot.rates_count,
        }
        for snapshot in snapshots
    ]
    latest = payloads[0] if payloads else None
    quality = multi_timeframe_summary(payloads)
    price_action = price_action_summary(latest)
    execution_cost = spread_slippage_summary(latest)
    execution_allowed = quality["status"] == "ok" and price_action["status"] == "ok" and execution_cost["status"] == "ok"
    return {
        "symbol": symbol.upper(),
        "execution_allowed_by_market_data": execution_allowed,
        "multi_timeframe": quality,
        "price_action": price_action,
        "spread_slippage": execution_cost,
    }
