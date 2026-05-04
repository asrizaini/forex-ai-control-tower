from __future__ import annotations

import math
import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from news_feed.adapter import evaluate_news_status

from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import AnalysisSnapshot, HistoricalCandle, MarketSnapshot, SignalRecord, Strategy, StrategyLabJob, TradingPair, WorkerStatus
from ..permissions import has_permission
from ..time_utils import iso_local
from strategies.lab import deterministic_backtest_result
from strategies.registry import discover_plugins, plugin_metadata

router = APIRouter(tags=["trading"])

DEFAULT_PAIRS = [
    ("EURUSD", "EUR/USD", True, "M1", "trend_pullback_v1"),
    ("GBPUSD", "GBP/USD", True, "M1", "trend_pullback_v1"),
    ("USDJPY", "USD/JPY", True, "M1", "trend_pullback_v1"),
    ("XAUUSD", "Gold / USD", True, "M1", "trend_pullback_v1"),
    ("AUDUSD", "AUD/USD", False, "M1", "trend_pullback_v1"),
    ("USDCAD", "USD/CAD", False, "M1", "trend_pullback_v1"),
    ("USDCHF", "USD/CHF", False, "M1", "trend_pullback_v1"),
    ("NZDUSD", "NZD/USD", False, "M1", "trend_pullback_v1"),
]


class TradingPairPayload(BaseModel):
    symbol: str = Field(min_length=3, max_length=40)
    display_name: str = Field(default="", max_length=80)
    enabled: bool = True
    default_timeframe: str = Field(default="M1", max_length=20)
    assigned_strategy_id: str | None = Field(default=None, max_length=100)
    status: str = Field(default="configured", max_length=60)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class BacktestRunPayload(BaseModel):
    symbol: str = Field(min_length=3, max_length=40)
    timeframe: str = Field(default="M1", max_length=20)
    strategy_id: str = Field(default="trend_pullback_v1", max_length=100)
    date_from: str = Field(default="", max_length=40)
    date_to: str = Field(default="", max_length=40)
    parameters_json: dict[str, Any] = Field(default_factory=dict)


def _now() -> datetime:
    return datetime.utcnow()


def _iso(value: datetime | None) -> str | None:
    return iso_local(value) if value else None


def _seed_pairs(db: Session) -> None:
    changed = False
    for symbol, display_name, enabled, timeframe, strategy_id in DEFAULT_PAIRS:
        existing = db.scalar(select(TradingPair).where(TradingPair.symbol == symbol))
        if existing:
            continue
        db.add(
            TradingPair(
                symbol=symbol,
                display_name=display_name,
                enabled=enabled,
                default_timeframe=timeframe,
                assigned_strategy_id=strategy_id,
                status="enabled" if enabled else "disabled",
                metadata_json={"source": "default_seed"},
            )
        )
        changed = True
    if changed:
        db.commit()


def _pair_dict(row: TradingPair) -> dict[str, Any]:
    return {
        "symbol": row.symbol,
        "display_name": row.display_name or row.symbol,
        "enabled": row.enabled,
        "default_timeframe": row.default_timeframe,
        "assigned_strategy_id": row.assigned_strategy_id,
        "status": row.status,
        "last_processed_at": _iso(row.last_processed_at),
        "metadata_json": row.metadata_json or {},
        "updated_at": _iso(row.updated_at),
    }


def _latest_snapshot(db: Session, symbol: str) -> MarketSnapshot | None:
    return db.scalar(select(MarketSnapshot).where(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc()).limit(1))


def _latest_candles(db: Session, symbol: str, timeframe: str, limit: int = 120) -> list[HistoricalCandle]:
    return list(
        db.scalars(
            select(HistoricalCandle)
            .where(HistoricalCandle.symbol == symbol, HistoricalCandle.timeframe == timeframe)
            .order_by(HistoricalCandle.candle_time.desc())
            .limit(limit)
        )
    )


def _tf_seconds(timeframe: str) -> int:
    value = timeframe.upper()
    if value.startswith("M"):
        return max(60, int(value[1:] or 1) * 60)
    if value.startswith("H"):
        return max(3600, int(value[1:] or 1) * 3600)
    if value.startswith("D"):
        return 86400
    return 60


def _candle_analysis(candles: list[HistoricalCandle], timeframe: str) -> dict[str, Any]:
    if not candles:
        return {
            "status": "missing",
            "direction": "neutral",
            "summary": "No candle data is available yet.",
            "missing_candles": True,
            "stale": True,
        }
    latest = candles[0]
    open_price = latest.open or 0.0
    close = latest.close or 0.0
    high = latest.high or max(open_price, close)
    low = latest.low or min(open_price, close)
    body = abs(close - open_price)
    full_range = max(high - low, 0.0)
    upper_wick = max(0.0, high - max(open_price, close))
    lower_wick = max(0.0, min(open_price, close) - low)
    direction = "bullish" if close > open_price else "bearish" if close < open_price else "neutral"
    age_seconds = max(0, int((_now() - latest.candle_time).total_seconds()))
    expected = _tf_seconds(timeframe)
    stale = age_seconds > expected * 3
    doji = full_range > 0 and body <= full_range * 0.12
    rejection = full_range > 0 and max(upper_wick, lower_wick) >= full_range * 0.55
    engulfing = False
    if len(candles) > 1:
        previous = candles[1]
        engulfing = (latest.high or 0) >= (previous.high or 0) and (latest.low or 0) <= (previous.low or 0) and body > abs((previous.close or 0) - (previous.open or 0))
    momentum = full_range > 0 and body >= full_range * 0.7
    breakout = len(candles) > 20 and (close >= max((c.high or close) for c in candles[1:20]) or close <= min((c.low or close) for c in candles[1:20]))
    return {
        "status": "stale" if stale else "ok",
        "direction": direction,
        "body_size": round(body, 6),
        "upper_wick_size": round(upper_wick, 6),
        "lower_wick_size": round(lower_wick, 6),
        "doji": doji,
        "indecision": doji,
        "rejection": rejection,
        "engulfing": engulfing,
        "momentum": momentum,
        "breakout": breakout,
        "missing_candles": len(candles) < 20,
        "stale": stale,
        "age_seconds": age_seconds,
        "last_candle_timestamp": _iso(latest.candle_time),
        "summary": f"{timeframe} candle is {direction}; body {round(body, 6)}, upper wick {round(upper_wick, 6)}, lower wick {round(lower_wick, 6)}.",
    }


def _trend_analysis(candles: list[HistoricalCandle]) -> dict[str, Any]:
    closes = [float(c.close) for c in reversed(candles) if c.close is not None]
    if len(closes) < 20:
        return {"status": "unclear", "bias": "neutral", "summary": "Insufficient candle history for trend detection."}
    fast = sum(closes[-5:]) / 5
    slow = sum(closes[-20:]) / 20
    if math.isclose(fast, slow, rel_tol=0.0001, abs_tol=0.0001):
        trend = "ranging"
        bias = "neutral"
    elif fast > slow:
        trend = "uptrend"
        bias = "bullish"
    else:
        trend = "downtrend"
        bias = "bearish"
    return {"status": trend, "bias": bias, "fast_average": round(fast, 6), "slow_average": round(slow, 6), "summary": f"Fast average is {round(fast, 6)} vs slow average {round(slow, 6)}; trend reads {trend}."}


def _latest_signal(db: Session, symbol: str, timeframe: str) -> SignalRecord | None:
    return db.scalar(
        select(SignalRecord)
        .where(SignalRecord.symbol == symbol, SignalRecord.timeframe == timeframe)
        .order_by(SignalRecord.created_at.desc())
        .limit(1)
    )


def _signal_dict(signal: SignalRecord | None) -> dict[str, Any]:
    if not signal:
        return {"direction": "no signal", "signal_status": "no_signal", "confidence": 0.0, "timestamp": None, "freshness_status": "missing"}
    return {
        "signal_id": signal.signal_id,
        "pair": signal.symbol,
        "timeframe": signal.timeframe,
        "direction": signal.direction,
        "confidence": signal.confidence,
        "entry_idea": signal.entry_idea,
        "stop_loss_idea": signal.stop_loss_idea,
        "take_profit_idea": signal.take_profit_idea,
        "strategy_used": signal.strategy_id,
        "reason": signal.reason,
        "blockers": signal.blockers,
        "risk_notes": signal.risk_notes,
        "freshness_status": signal.freshness_status,
        "signal_status": signal.signal_status,
        "timestamp": _iso(signal.created_at),
        "analysis": signal.analysis_json,
    }


def _build_pair_summary(db: Session, pair: TradingPair) -> dict[str, Any]:
    symbol = pair.symbol
    timeframe = pair.default_timeframe or "M1"
    snapshot = _latest_snapshot(db, symbol)
    candles = _latest_candles(db, symbol, timeframe)
    candle = _candle_analysis(candles, timeframe)
    trend = _trend_analysis(candles)
    news = evaluate_news_status(symbol)
    signal = _latest_signal(db, symbol, timeframe)
    stale = bool(candle.get("stale")) or (snapshot is None) or (snapshot.freshness_seconds is not None and snapshot.freshness_seconds > 180)
    signal_stale = signal is None or (_now() - signal.created_at) > timedelta(minutes=15)
    current_bias = "stale" if stale else trend["bias"]
    if news.get("news_halt_active"):
        final = "Blocked"
    elif stale:
        final = "Stale"
    elif trend["bias"] == "bullish":
        final = "Bullish"
    elif trend["bias"] == "bearish":
        final = "Bearish"
    else:
        final = "Neutral"
    return {
        "pair": symbol,
        "symbol": symbol,
        "display_name": pair.display_name or symbol,
        "enabled": pair.enabled,
        "current_price": (snapshot.payload_json or {}).get("last_price") if snapshot else None,
        "timeframe": timeframe,
        "last_candle_timestamp": candle.get("last_candle_timestamp"),
        "last_signal_timestamp": _iso(signal.created_at) if signal else None,
        "data_freshness_status": "stale" if stale else "fresh",
        "candle_status": candle.get("status"),
        "current_bias": current_bias,
        "trend_status": "stale" if stale else trend["status"],
        "signal_status": "stale" if signal_stale and signal else _signal_dict(signal)["signal_status"],
        "signal_confidence": signal.confidence if signal else 0.0,
        "technical_summary": trend["summary"],
        "fundamental_summary": news.get("note", "News/fundamental status unavailable."),
        "candle_summary": candle["summary"],
        "risk_summary": "Blocked by high-impact news window." if news.get("news_halt_active") else "Risk validation is monitor-only and no execution is authorized.",
        "final_conclusion": final,
        "candle_analysis": candle,
        "trend_analysis": trend,
        "news_status": news,
        "signal": _signal_dict(signal),
        "last_updated_time": _iso(snapshot.created_at if snapshot else pair.updated_at),
    }


def _store_analysis_snapshot(db: Session, analysis_type: str, summary: dict[str, Any]) -> None:
    db.add(
        AnalysisSnapshot(
            snapshot_id=f"{analysis_type}_{summary['symbol']}_{secrets.token_hex(6)}",
            analysis_type=analysis_type,
            symbol=summary["symbol"],
            timeframe=summary["timeframe"],
            confidence=summary.get("signal_confidence", 0.0),
            status=str(summary.get("final_conclusion", "Incomplete")).lower(),
            summary=str(summary.get(f"{analysis_type}_summary", summary.get("technical_summary", ""))),
            inputs_json={"pair_summary": True, "news_status": summary.get("news_status", {})},
            output_json=summary,
        )
    )


def _generate_signal_for_summary(db: Session, summary: dict[str, Any], strategy_id: str | None) -> SignalRecord:
    blockers: list[str] = []
    if summary["data_freshness_status"] == "stale":
        blockers.append("stale_market_or_candle_data")
    if summary.get("news_status", {}).get("news_halt_active"):
        blockers.append("high_impact_news_window")
    trend_bias = summary.get("trend_analysis", {}).get("bias", "neutral")
    candle_direction = summary.get("candle_analysis", {}).get("direction", "neutral")
    if blockers:
        direction = "hold"
        signal_status = "blocked"
        confidence = 0.0
        reason = "Signal blocked because " + ", ".join(blockers) + "."
    elif trend_bias == "bullish" and candle_direction in {"bullish", "neutral"}:
        direction = "buy"
        signal_status = "buy"
        confidence = 72.0
        reason = "Trend bias is bullish and latest candle does not conflict."
    elif trend_bias == "bearish" and candle_direction in {"bearish", "neutral"}:
        direction = "sell"
        signal_status = "sell"
        confidence = 72.0
        reason = "Trend bias is bearish and latest candle does not conflict."
    else:
        direction = "hold"
        signal_status = "hold"
        confidence = 45.0
        reason = "Trend and candle context are neutral or conflicting."
    signal = SignalRecord(
        signal_id=f"sig_{summary['symbol']}_{secrets.token_hex(8)}",
        symbol=summary["symbol"],
        timeframe=summary["timeframe"],
        direction=direction,
        confidence=confidence,
        signal_status=signal_status,
        freshness_status=summary["data_freshness_status"],
        strategy_id=strategy_id,
        entry_idea="Wait for confirmation; monitor-only signal." if direction == "hold" else "Use demo/manual approval workflow only; no auto execution.",
        stop_loss_idea="Derived by approved strategy/risk policy before execution.",
        take_profit_idea="Derived by approved strategy/risk policy before execution.",
        reason=reason,
        blockers=blockers,
        risk_notes=summary["risk_summary"],
        analysis_json=summary,
    )
    db.add(signal)
    return signal


@router.get("/trading-pairs")
def list_trading_pairs(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_pairs(db)
    rows = db.scalars(select(TradingPair).order_by(TradingPair.enabled.desc(), TradingPair.symbol.asc())).all()
    return {"items": [_pair_dict(row) for row in rows]}


@router.get("/trading-pairs/enabled")
def enabled_trading_pairs(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_pairs(db)
    rows = db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())).all()
    return {"symbols": [row.symbol for row in rows], "items": [_pair_dict(row) for row in rows]}


@router.post("/trading-pairs")
def create_trading_pair(payload: TradingPairPayload, db: Session = Depends(get_db), principal=Depends(current_principal)) -> dict[str, Any]:
    if not has_permission(principal.role, "system:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    symbol = payload.symbol.upper().strip()
    if db.scalar(select(TradingPair).where(TradingPair.symbol == symbol)):
        raise HTTPException(status_code=409, detail="Trading pair already exists")
    row = TradingPair(**{**payload.model_dump(), "symbol": symbol, "status": "enabled" if payload.enabled else "disabled"})
    db.add(row)
    audit(db, principal, "create", "trading_pair", symbol, {"enabled": payload.enabled, "timeframe": payload.default_timeframe})
    db.commit()
    db.refresh(row)
    return {"status": "created", "pair": _pair_dict(row)}


@router.put("/trading-pairs/{symbol}")
def update_trading_pair(symbol: str, payload: TradingPairPayload, db: Session = Depends(get_db), principal=Depends(current_principal)) -> dict[str, Any]:
    if not has_permission(principal.role, "system:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    _seed_pairs(db)
    row = db.scalar(select(TradingPair).where(TradingPair.symbol == symbol.upper()))
    if not row:
        row = TradingPair(symbol=symbol.upper())
        db.add(row)
    row.display_name = payload.display_name or row.symbol
    row.enabled = payload.enabled
    row.default_timeframe = payload.default_timeframe.upper()
    row.assigned_strategy_id = payload.assigned_strategy_id or None
    row.status = "enabled" if payload.enabled else "disabled"
    row.metadata_json = payload.metadata_json
    row.updated_at = _now()
    audit(db, principal, "update", "trading_pair", row.symbol, {"enabled": row.enabled, "timeframe": row.default_timeframe, "strategy": row.assigned_strategy_id})
    db.commit()
    return {"status": "saved", "pair": _pair_dict(row)}


@router.delete("/trading-pairs/{symbol}")
def delete_trading_pair(symbol: str, db: Session = Depends(get_db), principal=Depends(current_principal)) -> dict[str, Any]:
    if not has_permission(principal.role, "system:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    row = db.scalar(select(TradingPair).where(TradingPair.symbol == symbol.upper()))
    if not row:
        raise HTTPException(status_code=404, detail="Trading pair not found")
    row.enabled = False
    row.status = "disabled"
    row.updated_at = _now()
    audit(db, principal, "disable", "trading_pair", row.symbol)
    db.commit()
    return {"status": "disabled", "symbol": row.symbol}


@router.post("/analysis/run")
def run_analysis(db: Session = Depends(get_db), principal=Depends(current_principal)) -> dict[str, Any]:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    _seed_pairs(db)
    summaries = []
    rows = db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())).all()
    for pair in rows:
        summary = _build_pair_summary(db, pair)
        _store_analysis_snapshot(db, "technical", summary)
        _store_analysis_snapshot(db, "fundamental", summary)
        _store_analysis_snapshot(db, "candle", summary)
        _store_analysis_snapshot(db, "trend", summary)
        _generate_signal_for_summary(db, summary, pair.assigned_strategy_id)
        pair.last_processed_at = _now()
        pair.status = "processed_stale" if summary["data_freshness_status"] == "stale" else "processed"
        summaries.append(summary)
    for worker_id in ("technical_analysis_worker", "fundamental_analysis_worker", "signal_generation_worker", "risk_analysis_worker"):
        worker = db.scalar(select(WorkerStatus).where(WorkerStatus.worker_id == worker_id))
        if worker:
            worker.status = "running"
            worker.last_run_at = _now()
            worker.next_run_at = _now() + timedelta(minutes=5)
            worker.health_json = {
                "pairs_processed": len(rows),
                "stale_pairs": sum(1 for item in summaries if item["data_freshness_status"] == "stale"),
                "valid_signals": sum(1 for item in summaries if item["signal"]["direction"] in {"buy", "sell"}),
                "blocked_signals": sum(1 for item in summaries if item["signal"]["signal_status"] == "blocked"),
            }
    audit(db, principal, "run", "analysis_pipeline", "all_enabled_pairs", {"pairs_processed": len(rows), "signal_generation_approved_by_operator": True})
    db.commit()
    return {"status": "completed", "pairs_processed": len(rows), "items": summaries}


@router.get("/pair-summaries")
def pair_summaries(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_pairs(db)
    pairs = db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())).all()
    items = [_build_pair_summary(db, pair) for pair in pairs]
    buckets = {
        "bullish": [item["symbol"] for item in items if item["current_bias"] == "bullish"],
        "bearish": [item["symbol"] for item in items if item["current_bias"] == "bearish"],
        "neutral": [item["symbol"] for item in items if item["current_bias"] == "neutral"],
        "conflicting": [item["symbol"] for item in items if item["final_conclusion"] == "Wait"],
        "stale": [item["symbol"] for item in items if item["data_freshness_status"] == "stale"],
        "no_valid_signal": [item["symbol"] for item in items if item["signal_status"] in {"no_signal", "hold", "stale"}],
        "blocked": [item["symbol"] for item in items if item["signal_status"] == "blocked" or item["final_conclusion"] == "Blocked"],
        "missing_data": [item["symbol"] for item in items if item["candle_analysis"].get("missing_candles")],
    }
    return {"items": items, "summary": buckets, "updated_at": _iso(_now())}


@router.get("/signals/records")
def signal_records(symbol: str | None = None, limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> dict[str, Any]:
    query = select(SignalRecord)
    if symbol:
        query = query.where(SignalRecord.symbol == symbol.upper())
    rows = db.scalars(query.order_by(SignalRecord.created_at.desc()).limit(limit)).all()
    return {"items": [_signal_dict(row) for row in rows]}


@router.get("/signals/summary")
def signal_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    summaries = pair_summaries(db)
    return {"items": [item["signal"] for item in summaries["items"]], "summary": summaries["summary"], "updated_at": summaries["updated_at"]}


@router.get("/strategies/summary")
def strategy_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    strategies = db.scalars(select(Strategy).order_by(Strategy.strategy_id.asc())).all()
    pairs = db.scalars(select(TradingPair).order_by(TradingPair.symbol.asc())).all()
    jobs = db.scalars(select(StrategyLabJob).order_by(StrategyLabJob.created_at.desc()).limit(200)).all()
    items = [
            {
                "strategy_id": strategy.strategy_id,
                "name": strategy.name,
                "enabled": strategy.lifecycle_state in {"approved_for_manual", "approved_for_demo_auto", "approved_for_live_restricted", "demo_testing"},
                "lifecycle_state": strategy.lifecycle_state,
                "live_approval_status": strategy.live_approval_status,
                "assigned_pairs": [pair.symbol for pair in pairs if pair.assigned_strategy_id == strategy.strategy_id],
                "performance_summary": {
                    "tests": sum(1 for job in jobs if job.strategy_id == strategy.strategy_id),
                    "best_quality_score": max([job.quality_score or 0 for job in jobs if job.strategy_id == strategy.strategy_id], default=0),
                },
                "validation": "passed_for_demo_signal_generation" if strategy.lifecycle_state != "draft" else "needs_testing",
            }
            for strategy in strategies
        ]
    known = {item["strategy_id"] for item in items}
    for plugin in discover_plugins():
        if plugin.strategy_id in known:
            continue
        metadata = plugin_metadata(plugin)
        items.append(
            {
                "strategy_id": plugin.strategy_id,
                "name": plugin.name,
                "enabled": plugin.lifecycle != "draft",
                "lifecycle_state": plugin.lifecycle,
                "live_approval_status": "not_approved",
                "assigned_pairs": [pair.symbol for pair in pairs if pair.assigned_strategy_id == plugin.strategy_id],
                "performance_summary": {
                    "tests": sum(1 for job in jobs if job.strategy_id == plugin.strategy_id),
                    "best_quality_score": max([job.quality_score or 0 for job in jobs if job.strategy_id == plugin.strategy_id], default=0),
                },
                "validation": "passed_for_demo_signal_generation" if plugin.lifecycle != "draft" else "needs_testing",
                "metadata": metadata,
            }
        )
    return {"items": items}


@router.post("/testing/backtests/run")
def run_backtest(payload: BacktestRunPayload, db: Session = Depends(get_db), principal=Depends(current_principal)) -> dict[str, Any]:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    result = deterministic_backtest_result(payload.strategy_id, payload.symbol.upper(), payload.timeframe.upper())
    job = StrategyLabJob(
        job_id=f"bt_{secrets.token_hex(8)}",
        job_type="backtest",
        strategy_id=payload.strategy_id,
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe.upper(),
        status="completed",
        parameters_json={**payload.parameters_json, "date_from": payload.date_from, "date_to": payload.date_to},
        result_json=result,
        quality_score=result["quality_score"],
        created_by=principal.user_id,
        updated_at=_now(),
    )
    db.add(job)
    audit(db, principal, "run", "backtest", job.job_id, {"strategy_id": payload.strategy_id, "symbol": payload.symbol.upper()})
    db.commit()
    return {"status": "completed", "job_id": job.job_id, "result": result}


@router.get("/testing/backtests")
def testing_backtests(db: Session = Depends(get_db), limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    jobs = db.scalars(select(StrategyLabJob).where(StrategyLabJob.job_type == "backtest").order_by(StrategyLabJob.created_at.desc()).limit(limit)).all()
    return {
        "items": [
            {
                "job_id": job.job_id,
                "strategy_id": job.strategy_id,
                "symbol": job.symbol,
                "timeframe": job.timeframe,
                "status": job.status,
                "quality_score": job.quality_score,
                "result": job.result_json,
                "created_at": _iso(job.created_at),
            }
            for job in jobs
        ]
    }
