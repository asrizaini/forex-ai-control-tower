from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from broker_compatibility.checker import check_symbol_metadata, summarize_broker_compatibility

from ..auth import Principal
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..permissions import has_permission
from ..credential_store import runtime_value

router = APIRouter(prefix="/prelive", tags=["prelive"])


def _bridge_request(path: str) -> dict[str, Any]:
    token = runtime_value("BRIDGE_API_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="BRIDGE_API_TOKEN is not configured")
    url = f"{runtime_value('MT5_BRIDGE_URL', 'http://10.10.1.86:8501').rstrip('/')}{path}"
    request = urllib.request.Request(url, headers={"X-Bridge-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"MT5 bridge returned status {exc.code}") from exc
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"MT5 bridge request failed: {type(exc).__name__}") from exc


def _require_admin(principal: Principal) -> None:
    if not has_permission(principal.role, "deployment:write"):
        raise HTTPException(status_code=403, detail="Permission denied")


@router.get("")
def list_resource() -> dict:
    return {
        "module": "prelive",
        "description": "Pre-live evidence collection for broker compatibility, security review, and explicit live approval",
        "mode": "approval-required",
    }


@router.post("/broker-compatibility/check")
def broker_compatibility_check(
    symbols: list[str] | None = Body(default=None),
    persist: bool = False,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_admin(principal)
    requested = [
        item.strip().upper()
        for item in (
            symbols
            or [
                "EURUSD",
                "GBPUSD",
                "USDJPY",
                "XAUUSD",
                "AUDUSD",
                "USDCAD",
                "USDCHF",
                "NZDUSD",
            ]
        )
        if item.strip()
    ]
    available = set(_bridge_request("/symbols").get("symbols", []))
    results: list[dict[str, Any]] = []
    for symbol in requested:
        if symbol not in available:
            results.append({"symbol": symbol, "passed": False, "checks": {"symbol_available": False}, "metadata": {}})
            continue
        safe_symbol = urllib.parse.quote(symbol, safe="")
        info = _bridge_request(f"/symbols/{safe_symbol}/info").get("info", {})
        results.append(check_symbol_metadata(symbol, info))
    summary = summarize_broker_compatibility(results)
    if persist and summary["passed"]:
        audit(db, principal, "prelive_gate_passed", "prelive_gate", "broker_compatibility", summary)
        db.commit()
    return summary


@router.post("/security-review/record")
def record_security_review(
    checklist: dict[str, bool],
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_admin(principal)
    required = {
        "secret_rotation_confirmed",
        "dependency_scan_reviewed",
        "firewall_reviewed",
        "log_redaction_reviewed",
        "mt5_execution_reviewed",
        "rollback_reviewed",
    }
    missing = required - set(checklist)
    failed = sorted(key for key, passed in checklist.items() if key in required and not passed)
    if missing or failed:
        raise HTTPException(status_code=400, detail={"missing": sorted(missing), "failed": failed})
    audit(db, principal, "prelive_gate_passed", "prelive_gate", "security_review", {"checklist": checklist})
    db.commit()
    return {"passed": True, "gate": "security_review"}


@router.post("/production-live/approve")
def approve_production_live(
    confirmation: str = Body(embed=True),
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_admin(principal)
    if confirmation != "I explicitly approve production-live after demo validation":
        raise HTTPException(status_code=400, detail="Exact confirmation phrase required")
    audit(
        db,
        principal,
        "prelive_gate_passed",
        "prelive_gate",
        "production_live_explicitly_approved",
        {"confirmation": "operator_explicit_approval"},
    )
    db.commit()
    return {"approved": True, "gate": "production_live_explicitly_approved"}
