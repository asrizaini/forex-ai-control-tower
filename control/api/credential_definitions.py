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
    CredentialDefinition("TELEMETRY_INGEST_TOKEN", "Telemetry ingest token", "Core Runtime", False, True, "token64", min_length=32),
    CredentialDefinition("RECOVERY_EMAIL", "Recovery email", "Auth And Recovery", False, False, None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", placeholder="m.asri.kamaruddin@gmail.com"),
    CredentialDefinition("TOTP_ISSUER", "2FA issuer", "Auth And Recovery", False, False, None, placeholder="Forex AI Control Tower"),
    CredentialDefinition("LOCAL_AUTH_BOOTSTRAP_ENABLED", "Local bootstrap enabled", "Auth And Recovery", False, False, None, placeholder="false"),
    CredentialDefinition("LOCAL_ADMIN_BOOTSTRAP_PASSWORD", "Temporary admin password", "Auth And Recovery", False, True, "password24", min_length=12),
    CredentialDefinition("ALLOW_LIVE_TRADING", "Live trading runtime flag", "Trading Safety", False, False, None, placeholder="false"),
    CredentialDefinition("BRIDGE_MODE", "MT5 bridge mode", "Trading Safety", False, False, None, placeholder="demo"),
    CredentialDefinition("REQUIRE_ORDER_CHECK", "Require order_check", "Trading Safety", False, False, None, placeholder="true"),
    CredentialDefinition("NEWS_PROVIDER_ENABLED", "News provider enabled", "News", False, False, None, placeholder="true"),
    CredentialDefinition("NEWS_PROVIDER_TYPE", "News provider type", "News", False, False, None, placeholder="fmp_economic_calendar"),
    CredentialDefinition("NEWS_PROVIDER_API_KEY", "FMP/news API key", "News", True, True, None, min_length=8),
    CredentialDefinition("NEWS_HIGH_IMPACT_WINDOW_MINUTES", "News halt window minutes", "News", False, False, None, placeholder="45", pattern=r"^\d+$"),
    CredentialDefinition("NEWS_STALE_AFTER_MINUTES", "News stale after minutes", "News", False, False, None, placeholder="720", pattern=r"^\d+$"),
    CredentialDefinition("NEWS_CALENDAR_FROM", "News calendar from", "News", False, False, None, placeholder="YYYY-MM-DD"),
    CredentialDefinition("NEWS_CALENDAR_TO", "News calendar to", "News", False, False, None, placeholder="YYYY-MM-DD"),
    CredentialDefinition("TELEGRAM_BOT_TOKEN", "Telegram bot token", "Notifications", False, True, None, min_length=10),
    CredentialDefinition("TELEGRAM_ADMIN_CHAT_ID", "Telegram admin chat ID", "Notifications", False, True, None, min_length=3),
    CredentialDefinition("WHATSAPP_TOKEN", "WhatsApp token", "Notifications", False, True, None),
    CredentialDefinition("WHATSAPP_PHONE_NUMBER_ID", "WhatsApp phone number ID", "Notifications", False, True, None),
    CredentialDefinition("SMTP_HOST", "SMTP host", "Notifications", False, False, None),
    CredentialDefinition("SMTP_PORT", "SMTP port", "Notifications", False, False, None, placeholder="587", pattern=r"^\d+$"),
    CredentialDefinition("SMTP_USER", "SMTP user", "Notifications", False, True, None),
    CredentialDefinition("SMTP_PASSWORD", "SMTP password", "Notifications", False, True, None),
    CredentialDefinition("SMTP_FROM", "SMTP from address", "Notifications", False, False, None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    CredentialDefinition("FCM_PROJECT_ID", "FCM project ID", "Mobile Push", False, False, None),
    CredentialDefinition("FCM_SERVER_KEY", "FCM server key", "Mobile Push", False, True, None),
    CredentialDefinition("FCM_SERVICE_ACCOUNT_JSON", "FCM service account JSON", "Mobile Push", False, True, None),
    CredentialDefinition("VAPID_PUBLIC_KEY", "Browser push public key", "Browser Push", False, False, None),
    CredentialDefinition("VAPID_PRIVATE_KEY", "Browser push private key", "Browser Push", False, True, None),
    CredentialDefinition("OPENAI_API_KEY", "OpenAI API key", "Paid LLM", False, True, None),
    CredentialDefinition("GEMINI_API_KEY", "Gemini API key", "Paid LLM", False, True, None),
    CredentialDefinition("LLM_DAILY_BUDGET_USD", "Daily LLM budget USD", "Paid LLM", False, False, None, placeholder="0", pattern=r"^\d+(\.\d+)?$"),
    CredentialDefinition("LLM_MONTHLY_BUDGET_USD", "Monthly LLM budget USD", "Paid LLM", False, False, None, placeholder="0", pattern=r"^\d+(\.\d+)?$"),
    CredentialDefinition("PAID_LLM_APPROVAL_REQUIRED", "Paid LLM approval required", "Paid LLM", False, False, None, placeholder="true"),
    CredentialDefinition("OPENCLAW_ENABLED", "OpenClaw enabled", "OpenClaw", False, False, None, placeholder="false"),
    CredentialDefinition("OPENCLAW_API_URL", "OpenClaw API URL", "OpenClaw", False, False, None),
    CredentialDefinition("OPENCLAW_API_TOKEN", "OpenClaw API token", "OpenClaw", False, True, None),
    CredentialDefinition("GITHUB_OWNER", "GitHub owner", "Deployment Maintenance", False, False, None),
    CredentialDefinition("GITHUB_REPO", "GitHub repo", "Deployment Maintenance", False, False, None, placeholder="forex-ai-control-tower"),
    CredentialDefinition("GITHUB_TOKEN", "GitHub token", "Deployment Maintenance", False, True, None),
    CredentialDefinition("LINUX_STANDARD_SSH_PASSWORD", "Linux SSH password", "Deployment Maintenance", False, True, None),
    CredentialDefinition("LINUX_STANDARD_SUDO_PASSWORD", "Linux sudo password", "Deployment Maintenance", False, True, None),
    CredentialDefinition("WINDOWS_MT5_USER", "Windows MT5 user", "Deployment Maintenance", False, False, None),
    CredentialDefinition("WINDOWS_MT5_PASSWORD", "Windows WinRM password", "Deployment Maintenance", False, True, None),
    CredentialDefinition("WINDOWS_MT5_SSH_PASSWORD", "Windows SSH password", "Deployment Maintenance", False, True, None),
    CredentialDefinition("MT5_DEFAULT_ACCOUNT_ID", "MT5 default account ID", "MT5 Bridge", False, False, None, placeholder="demo_main"),
    CredentialDefinition("MT5_DEFAULT_BRIDGE_PORT", "MT5 default bridge port", "MT5 Bridge", False, False, None, placeholder="8501", pattern=r"^\d+$"),
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
