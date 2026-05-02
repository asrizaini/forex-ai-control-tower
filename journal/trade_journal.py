def record_trade(event: dict) -> dict:
    return {**event, "recorded": True}
