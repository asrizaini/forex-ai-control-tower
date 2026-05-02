from __future__ import annotations

import os
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

from execution_guard.approval_token import validate_approval_token

BRIDGE_MODE = os.getenv("BRIDGE_MODE", "demo")
ALLOW_LIVE_TRADING = os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"
REQUIRE_ORDER_CHECK = os.getenv("REQUIRE_ORDER_CHECK", "true").lower() == "true"

checked_orders: set[str] = set()
app = FastAPI(title="Forex AI MT5 Bridge", version="0.1.0")


class OrderRequest(BaseModel):
    client_order_id: str = Field(default_factory=lambda: f"order-{int(time.time())}")
    account_id: str
    symbol: str
    side: str
    volume: float
    live_order: bool = False


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "bridge_mode": BRIDGE_MODE,
        "allow_live_trading": ALLOW_LIVE_TRADING,
        "require_order_check": REQUIRE_ORDER_CHECK,
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/account")
def account() -> dict[str, Any]:
    return {"account_id": "demo-account", "mode": BRIDGE_MODE, "connected": False, "mock": True}


@app.get("/symbols")
def symbols() -> dict[str, Any]:
    return {"symbols": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"], "mock": True}


@app.get("/rates/{symbol}")
def rates(symbol: str) -> dict[str, Any]:
    return {"symbol": symbol, "timeframe": "M1", "rates": [], "mock": True}


@app.get("/ticks/{symbol}")
def ticks(symbol: str) -> dict[str, Any]:
    return {"symbol": symbol, "ticks": [], "mock": True}


@app.post("/order/check")
def order_check(order: OrderRequest) -> dict[str, Any]:
    if order.live_order and not ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled")
    checked_orders.add(order.client_order_id)
    return {"client_order_id": order.client_order_id, "check_passed": True, "mock": True}


@app.post("/order/send")
def order_send(order: OrderRequest, x_execution_guard_token: str | None = Header(default=None)) -> dict[str, Any]:
    if order.live_order and not ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled")
    if REQUIRE_ORDER_CHECK and order.client_order_id not in checked_orders:
        raise HTTPException(status_code=409, detail="order_check must run before order_send")
    if not validate_approval_token(x_execution_guard_token):
        raise HTTPException(status_code=403, detail="Execution Guard approval token required")
    return {
        "client_order_id": order.client_order_id,
        "mt5_order_id": None,
        "sent": False,
        "mock": True,
        "message": "Safe scaffold does not execute real MT5 orders",
    }


@app.get("/positions")
def positions() -> dict[str, Any]:
    return {"positions": [], "mock": True}


@app.get("/history")
def history() -> dict[str, Any]:
    return {"history": [], "mock": True}
