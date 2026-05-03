from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import Principal
from ..dependencies import current_principal
from openclaw_gateway.api_bridge import ALLOWED_ACTIONS, FORBIDDEN_ACTIONS, OPENCLAW_ENABLED, action_allowed, can_execute_trade

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


class OpenClawActionRequest(BaseModel):
    action: str = Field(max_length=120)
    approved: bool = False
    message: str = Field(default="", max_length=1000)


@router.get("")
def list_resource() -> dict:
    return {
        "module": "openclaw",
        "description": "Optional OpenClaw gateway, disabled by default",
        "mode": "production-required",
        "enabled": OPENCLAW_ENABLED,
        "can_execute_trade": can_execute_trade(),
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
    }


@router.post("/actions/check")
def check_action(payload: OpenClawActionRequest, principal: Principal = Depends(current_principal)) -> dict:
    allowed, reason = action_allowed(payload.action, payload.approved)
    return {
        "action": payload.action,
        "allowed": allowed,
        "reason": reason,
        "actor": principal.user_id,
        "trade_execution_allowed": False,
        "safe_summary": "OpenClaw may assist with approved human-facing API workflows only; it cannot execute trades or bypass governance.",
    }

