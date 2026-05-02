ESCALATION = {
    "info": ["dashboard"],
    "normal": ["dashboard", "telegram"],
    "warning": ["telegram", "mobile_push"],
    "critical": ["telegram", "whatsapp", "mobile_push", "email"],
    "emergency": ["dashboard", "telegram", "whatsapp", "mobile_push", "email", "browser_push"],
}


def channels_for(level: str) -> list[str]:
    return ESCALATION.get(level, ["dashboard"])
