def risk_allows_signal(policy: dict, exposure: dict) -> bool:
    if policy.get("kill_switch_active", False):
        return False
    return exposure.get("daily_loss", 0) <= policy.get("max_daily_loss", 0)
