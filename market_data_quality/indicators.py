from __future__ import annotations

from typing import Any


def _float_values(items: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for item in items:
        try:
            values.append(float(item[key]))
        except (KeyError, TypeError, ValueError):
            continue
    return values


def sma(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return round(sum(values[-period:]) / period, 6)


def ema(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    current = sum(values[:period]) / period
    for value in values[period:]:
        current = (value - current) * multiplier + current
    return round(current, 6)


def rsi(values: list[float], period: int = 14) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values[-period - 1 : -1], values[-period:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0
    rs = average_gain / average_loss
    return round(100 - (100 / (1 + rs)), 4)


def atr(rates: list[dict[str, Any]], period: int = 14) -> float | None:
    if period <= 0 or len(rates) <= period:
        return None
    highs = _float_values(rates, "high")
    lows = _float_values(rates, "low")
    closes = _float_values(rates, "close")
    if len(highs) != len(lows) or len(lows) != len(closes) or len(closes) <= period:
        return None
    true_ranges: list[float] = []
    for index in range(1, len(closes)):
        true_ranges.append(max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1])))
    return sma(true_ranges, period)


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, float | None]:
    if len(values) < slow + signal:
        return {"macd": None, "signal": None, "histogram": None}
    fast_values: list[float] = []
    slow_values: list[float] = []
    for index in range(slow, len(values) + 1):
        window = values[:index]
        fast_ema = ema(window, fast)
        slow_ema = ema(window, slow)
        if fast_ema is not None and slow_ema is not None:
            fast_values.append(fast_ema)
            slow_values.append(slow_ema)
    macd_values = [round(fast_item - slow_item, 6) for fast_item, slow_item in zip(fast_values, slow_values)]
    signal_value = ema(macd_values, signal)
    macd_value = macd_values[-1] if macd_values else None
    histogram = round(macd_value - signal_value, 6) if macd_value is not None and signal_value is not None else None
    return {"macd": macd_value, "signal": signal_value, "histogram": histogram}


def bollinger(values: list[float], period: int = 20, deviations: float = 2.0) -> dict[str, float | None]:
    mid = sma(values, period)
    if mid is None:
        return {"middle": None, "upper": None, "lower": None, "width": None}
    window = values[-period:]
    variance = sum((value - mid) ** 2 for value in window) / period
    stddev = variance**0.5
    upper = round(mid + deviations * stddev, 6)
    lower = round(mid - deviations * stddev, 6)
    width = round(upper - lower, 6)
    return {"middle": mid, "upper": upper, "lower": lower, "width": width}


def indicator_summary(rates: list[dict[str, Any]]) -> dict[str, Any]:
    closes = _float_values(rates, "close")
    return {
        "sma_20": sma(closes, 20),
        "sma_50": sma(closes, 50),
        "ema_20": ema(closes, 20),
        "ema_50": ema(closes, 50),
        "rsi_14": rsi(closes, 14),
        "atr_14": atr(rates, 14),
        "macd": macd(closes),
        "bollinger_20": bollinger(closes, 20),
    }
