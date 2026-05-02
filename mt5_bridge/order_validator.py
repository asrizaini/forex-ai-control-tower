def validate_order_payload(payload: dict) -> tuple[bool, str]:
    required = {"account_id", "symbol", "side", "volume"}
    missing = required - set(payload)
    if missing:
        return False, f"missing fields: {sorted(missing)}"
    if payload["side"] not in {"BUY", "SELL"}:
        return False, "side must be BUY or SELL internally"
    return True, "ok"
