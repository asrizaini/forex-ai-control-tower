from __future__ import annotations

ROLE_PERMISSIONS = {
    "super_admin": {
        "users:write",
        "accounts:write",
        "strategies:approve",
        "trades:approve",
        "risk:write",
        "system:halt",
        "audit:read",
        "agents:write",
        "deployment:write",
    },
    "strategy_admin": {"strategies:approve", "audit:read"},
    "account_manager": {"accounts:write", "trades:approve"},
    "extended_user": {"trades:approve:self", "notifications:write:self"},
    "viewer": {"dashboard:read"},
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
