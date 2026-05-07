from __future__ import annotations

import re
import secrets
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CredentialDefinition:
    name: str
    label: str
    category: str
    required: bool = False
    sensitive: bool = True
    generator: str | None = None
    placeholder: str = ""
    min_length: int = 1
    pattern: str | None = None
    restart_hint: str = "control-api"
    description: str = ""
    field_type: str = "text"
    options: tuple[str, ...] = ()

    def public_dict(self) -> dict:
        payload = asdict(self)
        payload.pop("pattern", None)
        return payload


DEFINITIONS: tuple[CredentialDefinition, ...] = (
    CredentialDefinition("POSTGRES_PASSWORD", "PostgreSQL password", "Core Runtime", True, True, "token64", min_length=12, description="Database password used by the control API and stack."),
    CredentialDefinition("GRAFANA_ADMIN_PASSWORD", "Grafana admin password", "Core Runtime", True, True, "password24", min_length=12),
    CredentialDefinition("JWT_SECRET_KEY", "JWT signing key", "Core Runtime", True, True, "token64", min_length=32),
    CredentialDefinition("EXECUTION_GUARD_SIGNING_KEY", "Execution Guard signing key", "Core Runtime", True, True, "token64", min_length=32),
    CredentialDefinition("BRIDGE_API_TOKEN", "MT5 bridge API token", "Core Runtime", True, True, "token64", min_length=32),
    CredentialDefinition("RECOVERY_EMAIL", "Recovery email", "Auth And Recovery", False, False, None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", placeholder="m.asri.kamaruddin@gmail.com", field_type="email"),
    CredentialDefinition("TOTP_ISSUER", "2FA issuer", "Auth And Recovery", False, False, None, placeholder="Forex AI Control Tower"),
    CredentialDefinition("LOCAL_AUTH_BOOTSTRAP_ENABLED", "Local bootstrap enabled", "Auth And Recovery", False, False, None, placeholder="false", field_type="boolean", options=("true", "false")),
    CredentialDefinition("LOCAL_ADMIN_BOOTSTRAP_PASSWORD", "Temporary admin password", "Auth And Recovery", False, True, "password24", min_length=12),
    CredentialDefinition("ALLOW_LIVE_TRADING", "Live trading runtime flag", "Trading Safety", False, False, None, placeholder="false", field_type="boolean", options=("true", "false")),
    CredentialDefinition("DEMO_GUARD_ENABLED", "Execution Guard for demo auto", "Trading Safety", False, False, None, placeholder="false", field_type="boolean", options=("true", "false")),
    CredentialDefinition("BRIDGE_MODE", "MT5 bridge mode", "Trading Safety", False, False, None, placeholder="demo", field_type="select", options=("demo", "live")),
    CredentialDefinition("REQUIRE_ORDER_CHECK", "Require order_check", "Trading Safety", False, False, None, placeholder="true", field_type="boolean", options=("true", "false")),
    CredentialDefinition("NEWS_PROVIDER_ENABLED", "News provider enabled", "News", False, False, None, placeholder="true", field_type="boolean", options=("true", "false")),
    CredentialDefinition("NEWS_PROVIDER_TYPE", "News provider type", "News", False, False, None, placeholder="fmp_economic_calendar", field_type="select", options=("fmp_economic_calendar", "manual_json", "https_json", "disabled")),
    CredentialDefinition("NEWS_PROVIDER_API_KEY", "FMP/news API key", "News", True, True, None, min_length=8),
    CredentialDefinition("NEWS_HIGH_IMPACT_WINDOW_MINUTES", "News halt window minutes", "News", False, False, None, placeholder="45", pattern=r"^\d+$", field_type="number"),
    CredentialDefinition("NEWS_STALE_AFTER_MINUTES", "News stale after minutes", "News", False, False, None, placeholder="720", pattern=r"^\d+$", field_type="number"),
    CredentialDefinition("NEWS_CALENDAR_FROM", "News calendar from", "News", False, False, None, placeholder="YYYY-MM-DD", field_type="date"),
    CredentialDefinition("NEWS_CALENDAR_TO", "News calendar to", "News", False, False, None, placeholder="YYYY-MM-DD", field_type="date"),
    CredentialDefinition("TELEGRAM_BOT_TOKEN", "Telegram bot token", "Notifications", False, True, None, min_length=10),
    CredentialDefinition("TELEGRAM_ADMIN_CHAT_ID", "Telegram admin chat ID", "Notifications", False, True, None, min_length=3),
    CredentialDefinition("ALERTMANAGER_WEBHOOK_TOKEN", "Alertmanager webhook token", "Notifications", False, True, "token64", min_length=16),
    CredentialDefinition("FCM_PROJECT_ID", "FCM project ID", "Mobile Push", False, False, None),
    CredentialDefinition("FCM_SERVER_KEY", "FCM server key", "Mobile Push", False, True, None),
    CredentialDefinition("FCM_SERVICE_ACCOUNT_JSON", "FCM service account JSON", "Mobile Push", False, True, None),
    CredentialDefinition("GEMINI_API_KEY", "Gemini API key", "Paid LLM", False, True, None),
    CredentialDefinition("LLM_DAILY_BUDGET_USD", "Daily LLM budget USD", "Paid LLM", False, False, None, placeholder="0", pattern=r"^\d+(\.\d+)?$", field_type="number"),
    CredentialDefinition("LLM_MONTHLY_BUDGET_USD", "Monthly LLM budget USD", "Paid LLM", False, False, None, placeholder="0", pattern=r"^\d+(\.\d+)?$", field_type="number"),
    CredentialDefinition("PAID_LLM_APPROVAL_REQUIRED", "Paid LLM approval required", "Paid LLM", False, False, None, placeholder="true", field_type="boolean", options=("true", "false")),
    CredentialDefinition("OPENCLAW_ENABLED", "OpenClaw enabled", "OpenClaw", False, False, None, placeholder="false", field_type="boolean", options=("true", "false")),
    CredentialDefinition("OPENCLAW_API_URL", "OpenClaw API URL", "OpenClaw", False, False, None),
    CredentialDefinition("OPENCLAW_API_TOKEN", "OpenClaw API token", "OpenClaw", False, True, None),
    CredentialDefinition("AGENT_EVENT_INGEST_TOKEN", "Agent theater ingest token", "OpenClaw", False, True, "token64", min_length=16),
    CredentialDefinition("TELEMETRY_INGEST_TOKEN", "Telemetry ingest token", "OpenClaw", False, True, "token64", min_length=16),
    CredentialDefinition("ORCHESTRATOR_CHAT_INTERNAL_MODE", "Orchestrator internal chat mode", "OpenClaw", False, False, None, placeholder="true", field_type="boolean", options=("true", "false")),
    CredentialDefinition("ORCHESTRATOR_GENERAL_CHAT_MODE", "Orchestrator chat backend", "OpenClaw", False, False, None, placeholder="local", field_type="select", options=("local", "disabled")),
    CredentialDefinition("ORCHESTRATOR_GENERAL_CHAT_MODEL", "Orchestrator local model", "OpenClaw", False, False, None, placeholder="llama3.1:8b"),
    CredentialDefinition("ORCHESTRATOR_LLM_TIMEOUT_SECONDS", "Orchestrator LLM timeout seconds", "OpenClaw", False, False, None, placeholder="8", pattern=r"^\d+$", field_type="number"),
    CredentialDefinition("OLLAMA_REASON_URL", "Local LLM base URL", "OpenClaw", False, False, None, placeholder="http://10.10.1.82:11434"),
    CredentialDefinition("LOCAL_LLM_API_STYLE", "Local LLM API style", "OpenClaw", False, False, None, placeholder="ollama", field_type="select", options=("ollama", "openai_compatible")),
    CredentialDefinition("LOCAL_LLM_API_KEY", "Local LLM API key (optional)", "OpenClaw", False, True, None),
    CredentialDefinition("ORCHESTRATOR_LLM_RETRY_COUNT", "Orchestrator LLM retries", "OpenClaw", False, False, None, placeholder="1", pattern=r"^[0-3]$", field_type="number"),
    CredentialDefinition("MT5_DEFAULT_ACCOUNT_ID", "MT5 default account ID", "MT5 Bridge", False, False, None, placeholder="demo_main"),
    CredentialDefinition("MT5_DEFAULT_BRIDGE_PORT", "MT5 default bridge port", "MT5 Bridge", False, False, None, placeholder="8501", pattern=r"^\d+$", field_type="number"),
    CredentialDefinition("MT5_BRIDGE_API_URL", "MT5 bridge API URL", "MT5 Bridge", False, False, None, placeholder="http://10.10.1.86:8501"),
    CredentialDefinition("MT5_BRIDGE_URL", "MT5 bridge base URL", "MT5 Bridge", False, False, None, placeholder="http://10.10.1.86:8501"),
    CredentialDefinition("MT5_DEFAULT_TERMINAL_PORT", "MT5 default terminal port", "MT5 Bridge", False, False, None, placeholder="8501", pattern=r"^\d+$", field_type="number"),
    CredentialDefinition("MT5_TERMINAL_PATH", "MT5 terminal path", "MT5 Bridge", False, False, None, placeholder=r"C:\Program Files\MetaTrader 5\terminal64.exe"),
    CredentialDefinition("MT5_ACCOUNT_PROFILES_FILE", "MT5 account profiles file", "MT5 Bridge", False, False, None, placeholder=r"C:\ForexAI\mt5_bridge\account_profiles.json"),
)

DEFINITION_BY_NAME = {definition.name: definition for definition in DEFINITIONS}


def validate_value(name: str, value: str) -> tuple[str, str]:
    definition = DEFINITION_BY_NAME.get(name)
    if not definition:
        return "unknown", "Unknown credential name"
    if not value:
        return ("missing", "Required value is missing") if definition.required else ("optional_missing", "Optional value is not configured")
    if len(value) < definition.min_length:
        return "invalid", f"Minimum length is {definition.min_length}"
    if name == "ORCHESTRATOR_GENERAL_CHAT_MODE":
        normalized = {"ollama": "local", "static": "disabled"}.get(value, value)
        if definition.options and normalized not in definition.options:
            return "invalid", f"Allowed values: {', '.join(definition.options)}"
        return "valid", f"Configured (normalized: {normalized})"
    if definition.options and value not in definition.options:
        return "invalid", f"Allowed values: {', '.join(definition.options)}"
    if definition.pattern and not re.match(definition.pattern, value):
        return "invalid", "Value format is invalid"
    return "valid", "Configured"


def generate_value(name: str) -> str:
    definition = DEFINITION_BY_NAME.get(name)
    generator = definition.generator if definition else None
    if generator == "token64":
        return secrets.token_urlsafe(48)
    if generator == "password24":
        return secrets.token_urlsafe(24)
    return secrets.token_urlsafe(32)
