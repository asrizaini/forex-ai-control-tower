from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_BRIDGE_URL = "http://10.10.1.86:8501"


def _bridge_url() -> str:
    return os.getenv("MT5_BRIDGE_URL", DEFAULT_BRIDGE_URL).rstrip("/")


def _token() -> str | None:
    return os.getenv("BRIDGE_API_TOKEN")


def _request(path: str, require_token: bool = True, timeout_seconds: int = 8) -> dict[str, Any]:
    url = f"{_bridge_url()}{path}"
    request = urllib.request.Request(url, method="GET")
    token = _token()
    if token:
        request.add_header("X-Bridge-Token", token)
    elif require_token:
        return {"ok": False, "status": 0, "error": "bridge_token_not_available", "url": url}
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8", errors="replace")
            body = json.loads(text) if text else {}
            return {
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "latency_ms": int((time.time() - started) * 1000),
                "body": body,
                "url": url,
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": "http_error", "url": url}
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": 0, "error": type(exc).__name__, "url": url}


def request_json(url: str, timeout_seconds: int = 8) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8", errors="replace")
            body = json.loads(text) if text else {}
            return {
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "latency_ms": int((time.time() - started) * 1000),
                "body": body,
                "url": url,
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": "http_error", "url": url}
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": 0, "error": type(exc).__name__, "url": url}


def bridge_health() -> dict[str, Any]:
    return _request("/health", require_token=False)


def bridge_account() -> dict[str, Any]:
    return _request("/account")


def bridge_symbols() -> dict[str, Any]:
    return _request("/symbols")


def bridge_rates(symbol: str) -> dict[str, Any]:
    safe_symbol = urllib.parse.quote(symbol, safe="")
    return _request(f"/rates/{safe_symbol}")


def bridge_ticks(symbol: str) -> dict[str, Any]:
    safe_symbol = urllib.parse.quote(symbol, safe="")
    return _request(f"/ticks/{safe_symbol}")


def bridge_positions() -> dict[str, Any]:
    return _request("/positions")


def bridge_history() -> dict[str, Any]:
    return _request("/history")


def mask_login(value: Any) -> str:
    text = str(value or "")
    if len(text) <= 3:
        return "***"
    return f"***{text[-3:]}"


def configured_watchlist() -> list[str]:
    raw = os.getenv("MARKET_WATCH_SYMBOLS", "EURUSD,XAUUSD,GBPUSD,USDJPY")
    return [item.strip().upper() for item in raw.split(",") if item.strip()]
