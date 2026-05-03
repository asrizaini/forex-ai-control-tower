from __future__ import annotations

import os
from typing import Any


REQUIRED_RUNTIME_SECRETS = (
    "POSTGRES_PASSWORD",
    "GRAFANA_ADMIN_PASSWORD",
    "JWT_SECRET_KEY",
    "EXECUTION_GUARD_SIGNING_KEY",
    "BRIDGE_API_TOKEN",
)


def secret_manager_status() -> dict[str, Any]:
    provider = os.getenv("SECRET_MANAGER_PROVIDER", "env").lower()
    required = {name: bool(os.getenv(name)) for name in REQUIRED_RUNTIME_SECRETS}
    external = {
        "vault": {"configured": bool(os.getenv("VAULT_ADDR") and os.getenv("VAULT_TOKEN"))},
        "sops": {"configured": bool(os.getenv("SOPS_AGE_KEY"))},
        "cloud": {"configured": bool(os.getenv("CLOUD_SECRET_PROVIDER"))},
    }
    return {
        "active_provider": provider,
        "env_provider_active": provider == "env",
        "required_runtime_secrets_present": all(required.values()),
        "required_runtime_secrets": required,
        "external_providers": external,
        "live_trading_secret_gate": provider != "env" and any(item["configured"] for item in external.values()),
        "notes": "Secret values are never returned by this endpoint.",
    }

