from __future__ import annotations

import os
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from control.api.credential_store import runtime_value

ALLOWED_ACTIONS = {"admin_chat", "user_chat", "daily_summaries", "status_queries", "approved_api_calls"}
FORBIDDEN_ACTIONS = {
    "direct_mt5_execution",
    "broker_password_access",
    "risk_engine_bypass",
    "admin_approval_bypass",
    "unrestricted_shell_commands",
    "direct_production_modification",
}


def _runtime_value(name: str, default: str = "") -> str:
    return runtime_value(name, default)


def _as_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def openclaw_enabled() -> bool:
    return _as_bool(_runtime_value("OPENCLAW_ENABLED", "false"))


def openclaw_runtime_url() -> str:
    return _runtime_value("OPENCLAW_API_URL", "").strip().rstrip("/")


def openclaw_runtime_token() -> str:
    return _runtime_value("OPENCLAW_API_TOKEN", "").strip()


def openclaw_runtime_configured() -> bool:
    return bool(openclaw_runtime_url())


def can_execute_trade() -> bool:
    return False


def action_allowed(action: str, approved: bool = False) -> tuple[bool, str]:
    if not openclaw_enabled():
        return False, "openclaw_disabled"
    if action in FORBIDDEN_ACTIONS or "execute" in action.lower() or "shell" in action.lower():
        return False, "forbidden_action"
    if action == "approved_api_calls" and not approved:
        return False, "approval_required"
    if action not in ALLOWED_ACTIONS:
        return False, "unknown_action"
    return True, "allowed"


def openclaw_status() -> dict[str, Any]:
    url = openclaw_runtime_url()
    return {
        "enabled": openclaw_enabled(),
        "runtime_configured": bool(url),
        "runtime_url_host": urllib.parse.urlparse(url).netloc if url else "",
        "can_execute_trade": False,
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
    }


def probe_openclaw_runtime_health() -> dict[str, Any]:
    if not openclaw_enabled():
        return {"ok": False, "reason": "openclaw_disabled"}
    base_url = openclaw_runtime_url()
    if not base_url:
        return {"ok": False, "reason": "openclaw_runtime_not_configured"}
    token = openclaw_runtime_token()
    endpoint = f"{base_url}/health"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            return {"ok": True, "status_code": response.status, "payload": parsed}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            detail = ""
        return {"ok": False, "reason": f"http_error_{exc.code}", "detail": detail}
    except Exception as exc:
        return {"ok": False, "reason": type(exc).__name__}


def call_openclaw_runtime(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not openclaw_enabled():
        return {"ok": False, "reason": "openclaw_disabled"}
    base_url = openclaw_runtime_url()
    if not base_url:
        return {"ok": False, "reason": "openclaw_runtime_not_configured"}
    token = openclaw_runtime_token()
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    endpoint = f"{base_url}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {"ok": True, "status_code": response.status, "raw": raw}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            detail = ""
        return {"ok": False, "reason": f"http_error_{exc.code}", "detail": detail}
    except Exception as exc:
        return {"ok": False, "reason": type(exc).__name__}
