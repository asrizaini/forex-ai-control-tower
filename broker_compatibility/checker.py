def check_broker_profile(profile: dict) -> tuple[bool, str]:
    required = {"symbols", "min_lot", "max_lot", "lot_step", "execution_mode"}
    missing = required - set(profile)
    if missing:
        return False, f"missing broker profile fields: {sorted(missing)}"
    return True, "broker profile accepted"
