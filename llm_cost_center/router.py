from __future__ import annotations

import os
import re


SECRET_PATTERN = re.compile(r"(password|token|secret|api[_-]?key|bearer\s+[a-z0-9._~+/=-]+)", re.IGNORECASE)


def redact_prompt(text: str) -> str:
    return SECRET_PATTERN.sub("[REDACTED]", text)


def provider_ready(provider: str) -> bool:
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "gemini":
        return bool(os.getenv("GEMINI_API_KEY"))
    if provider == "local":
        return True
    return False


def choose_provider(task_type: str, estimated_cost: float, daily_spend: float, daily_limit: float, paid_requested: bool = False) -> dict:
    if daily_spend + estimated_cost > daily_limit:
        return {"provider": "local", "reason": "budget_limit_fallback", "paid_allowed": False}
    if not paid_requested:
        return {"provider": "local", "reason": "local_default", "paid_allowed": False}
    for provider in ("openai", "gemini"):
        if provider_ready(provider):
            return {"provider": provider, "reason": f"{provider}_ready", "paid_allowed": True}
    return {"provider": "local", "reason": "paid_provider_not_configured_fallback", "paid_allowed": False}
