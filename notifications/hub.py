ESCALATION = {
    "info": ["dashboard"],
    "normal": ["dashboard", "telegram"],
    "warning": ["telegram", "mobile_push"],
    "critical": ["telegram", "whatsapp", "mobile_push", "email"],
    "emergency": ["dashboard", "telegram", "whatsapp", "mobile_push", "email", "browser_push"],
}


def channels_for(level: str) -> list[str]:
    return ESCALATION.get(level, ["dashboard"])


CHANNEL_ENV = {
    "telegram": ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ADMIN_CHAT_ID"),
    "whatsapp": ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID"),
    "mobile_push": ("FCM_SERVER_KEY", "FCM_PROJECT_ID"),
    "email": ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"),
    "browser_push": ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY"),
    "discord": ("DISCORD_WEBHOOK_URL",),
    "sms": ("SMS_PROVIDER_TOKEN",),
}


def channel_status(env: dict | None = None) -> dict:
    import os

    source = env or os.environ

    def configured(name: str) -> bool:
        if source.get(name):
            return True
        if env is not None:
            return False
        try:
            from control.api.credential_store import get_config_value
            from control.api.db import SessionLocal

            db = SessionLocal()
            try:
                return bool(get_config_value(db, name))
            finally:
                db.close()
        except Exception:
            return False

    status = {"dashboard": {"configured": True, "delivery_enabled": True, "missing": []}}
    for channel, required in CHANNEL_ENV.items():
        missing = [name for name in required if not configured(name)]
        status[channel] = {"configured": not missing, "delivery_enabled": not missing, "missing": missing}
    return status


def quiet_hours_allow(level: str, quiet_hours_enabled: bool) -> bool:
    return level in {"critical", "emergency"} or not quiet_hours_enabled


def route_notification(level: str, quiet_hours_enabled: bool = False, env: dict | None = None) -> dict:
    desired = channels_for(level)
    statuses = channel_status(env)
    allowed_by_quiet_hours = quiet_hours_allow(level, quiet_hours_enabled)
    routed = [channel for channel in desired if allowed_by_quiet_hours and statuses.get(channel, {}).get("delivery_enabled")]
    pending = [channel for channel in desired if channel not in routed]
    return {
        "level": level,
        "desired_channels": desired,
        "routed_channels": routed,
        "pending_channels": pending,
        "quiet_hours_allowed": allowed_by_quiet_hours,
        "channel_status": statuses,
    }
