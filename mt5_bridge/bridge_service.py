from __future__ import annotations

import os
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

from execution_guard.approval_token import validate_approval_token
try:
    from .mt5_client import MT5Client, MT5Unavailable
except ImportError:
    from mt5_client import MT5Client, MT5Unavailable

BRIDGE_MODE = os.getenv("BRIDGE_MODE", "demo")
ALLOW_LIVE_TRADING = os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"
REQUIRE_ORDER_CHECK = os.getenv("REQUIRE_ORDER_CHECK", "true").lower() == "true"

checked_orders: dict[str, dict[str, Any]] = {}
app = FastAPI(title="Forex AI MT5 Bridge", version="0.1.0")


class OrderRequest(BaseModel):
    client_order_id: str = Field(default_factory=lambda: f"order-{int(time.time())}")
    account_id: str
    symbol: str
    side: str
    volume: float
    live_order: bool = False
    price: float | None = None
    sl: float | None = None
    tp: float | None = None
    deviation: int = 20


def client() -> MT5Client:
    try:
        return MT5Client()
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def mt5_request(order: OrderRequest) -> dict[str, Any]:
    mt5 = client().mt5
    order_type = mt5.ORDER_TYPE_BUY if order.side == "BUY" else mt5.ORDER_TYPE_SELL
    request: dict[str, Any] = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": order.symbol,
        "volume": order.volume,
        "type": order_type,
        "deviation": order.deviation,
        "magic": 810081,
        "comment": f"forex-ai:{order.client_order_id}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if order.price is not None:
        request["price"] = order.price
    if order.sl is not None:
        request["sl"] = order.sl
    if order.tp is not None:
        request["tp"] = order.tp
    return request


@app.get("/health")
def health() -> dict[str, Any]:
    connected = False
    error = None
    try:
        connected = client().connect()
    except HTTPException as exc:
        error = exc.detail
    return {
        "status": "ok" if connected else "degraded",
        "bridge_mode": BRIDGE_MODE,
        "allow_live_trading": ALLOW_LIVE_TRADING,
        "require_order_check": REQUIRE_ORDER_CHECK,
        "mt5_connected": connected,
        "error": error,
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/account")
def account() -> dict[str, Any]:
    try:
        return client().account_info()
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/symbols")
def symbols() -> dict[str, Any]:
    try:
        return {"symbols": client().symbols()}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/rates/{symbol}")
def rates(symbol: str) -> dict[str, Any]:
    try:
        return {"symbol": symbol, "timeframe": "M1", "rates": client().rates(symbol)}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/ticks/{symbol}")
def ticks(symbol: str) -> dict[str, Any]:
    try:
        return {"symbol": symbol, "tick": client().ticks(symbol)}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/order/check")
def order_check(order: OrderRequest) -> dict[str, Any]:
    if order.live_order and not ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled")
    try:
        result = client().order_check(mt5_request(order))
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    checked_orders[order.client_order_id] = result
    return {"client_order_id": order.client_order_id, "check_passed": result.get("retcode") == 0, "result": result}


@app.post("/order/send")
def order_send(order: OrderRequest, x_execution_guard_token: str | None = Header(default=None)) -> dict[str, Any]:
    if order.live_order and not ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled")
    if REQUIRE_ORDER_CHECK and order.client_order_id not in checked_orders:
        raise HTTPException(status_code=409, detail="order_check must run before order_send")
    if not validate_approval_token(x_execution_guard_token):
        raise HTTPException(status_code=403, detail="Execution Guard approval token required")
    try:
        result = client().order_send(mt5_request(order))
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"client_order_id": order.client_order_id, "sent": True, "result": result}


@app.get("/positions")
def positions() -> dict[str, Any]:
    try:
        return {"positions": client().positions()}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/history")
def history() -> dict[str, Any]:
    try:
        return {"history": client().history()}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
