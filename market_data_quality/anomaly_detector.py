def detect_anomalies(candles: list[dict]) -> list[str]:
    return [] if candles else ["missing_candles"]
