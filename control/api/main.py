from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select
from starlette.responses import RedirectResponse
from starlette.responses import Response

from agent_theater.renderer import render_event

from .auth import decode_token
from .credential_store import runtime_bool
from .db import SessionLocal, init_db
from .models import Account
from .observability import JsonAccessLogAndMetricsMiddleware, collect_database_metrics
from .routes import (
    accounts,
    agents,
    agent_theater,
    approvals,
    audit,
    auth,
    backtests,
    credentials,
    control_center,
    data_retention,
    deployments,
    forward_tests,
    llm,
    localization,
    mobile,
    news,
    notifications,
    openclaw,
    permissions,
    prelive,
    risk,
    service_keys,
    signals,
    strategies,
    system,
    telemetry,
    trading,
    trades,
    tuning,
    users,
)

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Forex AI Control Tower",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://10.10.1.81:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(JsonAccessLogAndMetricsMiddleware)

    for router in [
        auth.router,
        users.router,
        accounts.router,
        agents.router,
        permissions.router,
        strategies.router,
        signals.router,
        trades.router,
        approvals.router,
        risk.router,
        service_keys.router,
        news.router,
        backtests.router,
        credentials.router,
        control_center.router,
        deployments.router,
        forward_tests.router,
        llm.router,
        tuning.router,
        notifications.router,
        prelive.router,
        agent_theater.router,
        system.router,
        telemetry.router,
        trading.router,
        openclaw.router,
        localization.router,
        mobile.router,
        audit.router,
        data_retention.router,
    ]:
        app.include_router(router, prefix=API_PREFIX)

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    init_db()

    def runtime_context() -> dict[str, object]:
        environment = "demo"
        trading_mode = "monitor_only"
        db = SessionLocal()
        try:
            account = db.scalar(
                select(Account).where(Account.enabled.is_(True)).order_by(Account.created_at.desc()).limit(1)
            )
            if account:
                environment = account.environment
                trading_mode = account.trading_mode
        finally:
            db.close()
        live_enabled = runtime_bool("ALLOW_LIVE_TRADING", False)
        live_auto = trading_mode in {"demo_auto", "restricted_live_auto"} and (
            environment == "demo" or (environment == "production-live" and live_enabled)
        )
        return {
            "environment": environment,
            "trading_mode": trading_mode,
            "live_auto_trading": live_auto,
        }

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", **runtime_context()}

    @app.get("/ready", tags=["system"])
    def ready() -> dict:
        return {"status": "ready"}

    @app.get("/api/status", tags=["system"])
    def root_api_status() -> dict:
        return {"status": "ok", "versioned_status": "/api/v1/api/status", "docs": "/docs", "metrics": "/metrics"}

    @app.get("/api/workers/status", tags=["system"])
    def root_workers_status() -> RedirectResponse:
        return RedirectResponse("/api/v1/workers/status")

    @app.get("/api/calendar/status", tags=["system"])
    def root_calendar_status() -> RedirectResponse:
        return RedirectResponse("/api/v1/calendar/status")

    @app.get("/api/news/status", tags=["system"])
    def root_news_status() -> RedirectResponse:
        return RedirectResponse("/api/v1/news/status")

    @app.get("/api/config/status", tags=["system"])
    def root_config_status() -> RedirectResponse:
        return RedirectResponse("/api/v1/config/status")

    @app.get("/metrics", tags=["system"])
    def metrics() -> Response:
        collect_database_metrics()
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    async def authenticated_ws(websocket: WebSocket, stream: str) -> None:
        token = websocket.query_params.get("token")
        if not token or not decode_token(token):
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        await websocket.accept()
        await websocket.send_json({"stream": stream, "status": "connected"})
        await websocket.close()

    @app.websocket("/ws/v1/system")
    async def ws_system(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "system")

    @app.websocket("/ws/v1/signals")
    async def ws_signals(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "signals")

    @app.websocket("/ws/v1/trades")
    async def ws_trades(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "trades")

    @app.websocket("/ws/v1/approvals")
    async def ws_approvals(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "approvals")

    @app.websocket("/ws/v1/risk")
    async def ws_risk(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "risk")

    @app.websocket("/ws/v1/agent-theater")
    async def ws_agent_theater(websocket: WebSocket) -> None:
        token = websocket.query_params.get("token")
        language = websocket.query_params.get("language", "en")
        internal_mode = os.getenv("AGENT_THEATER_INTERNAL_WS", "true").lower() == "true"
        if not internal_mode and (not token or not decode_token(token)):
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        await websocket.accept()
        event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
        last_size = 0
        while True:
            if event_log.exists():
                current_size = event_log.stat().st_size
                if current_size < last_size:
                    last_size = 0
                if current_size > last_size:
                    with event_log.open("r", encoding="utf-8") as handle:
                        handle.seek(last_size)
                        lines = handle.readlines()
                        last_size = handle.tell()
                    for line in lines[-20:]:
                        try:
                            await websocket.send_json(render_event(json.loads(line), language))
                        except json.JSONDecodeError:
                            continue
            await asyncio.sleep(1)

    @app.websocket("/ws/v1/accounts/{account_id}")
    async def ws_account(websocket: WebSocket, account_id: str) -> None:
        await authenticated_ws(websocket, f"accounts/{account_id}")

    @app.websocket("/ws/v1/users/{user_id}")
    async def ws_user(websocket: WebSocket, user_id: str) -> None:
        await authenticated_ws(websocket, f"users/{user_id}")

    return app


app = create_app()
