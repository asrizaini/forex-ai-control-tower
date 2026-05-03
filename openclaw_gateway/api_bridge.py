from __future__ import annotations

import os

OPENCLAW_ENABLED = os.getenv("OPENCLAW_ENABLED", "false").lower() == "true"
ALLOWED_ACTIONS = {"admin_chat", "user_chat", "daily_summaries", "status_queries", "approved_api_calls"}
FORBIDDEN_ACTIONS = {
    "direct_mt5_execution",
    "broker_password_access",
    "risk_engine_bypass",
    "admin_approval_bypass",
    "unrestricted_shell_commands",
    "direct_production_modification",
}


def can_execute_trade() -> bool:
    return False


def action_allowed(action: str, approved: bool = False) -> tuple[bool, str]:
    if not OPENCLAW_ENABLED:
        return False, "openclaw_disabled"
    if action in FORBIDDEN_ACTIONS or "execute" in action.lower() or "shell" in action.lower():
        return False, "forbidden_action"
    if action == "approved_api_calls" and not approved:
        return False, "approval_required"
    if action not in ALLOWED_ACTIONS:
        return False, "unknown_action"
    return True, "allowed"
