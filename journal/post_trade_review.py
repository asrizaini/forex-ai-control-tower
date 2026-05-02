def review_closed_trade(trade: dict) -> dict:
    return {"trade_id": trade.get("trade_id"), "reviewed": True}
