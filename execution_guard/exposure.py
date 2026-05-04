from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SYMBOL_CURRENCIES = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "XAUUSD": ("XAU", "USD"),
    "AUDUSD": ("AUD", "USD"),
    "USDCAD": ("USD", "CAD"),
    "USDCHF": ("USD", "CHF"),
    "NZDUSD": ("NZD", "USD"),
}


@dataclass(frozen=True)
class ExposureDecision:
    duplicate_trade_risk: bool
    correlation_exposure_ok: bool
    reasons: tuple[str, ...]
    related_position_count: int


def currencies_for_symbol(symbol: str) -> tuple[str, str] | tuple[()]:
    normalized = symbol.upper().strip()
    if normalized in SYMBOL_CURRENCIES:
        return SYMBOL_CURRENCIES[normalized]
    if len(normalized) >= 6:
        return (normalized[:3], normalized[3:6])
    return ()


def _same_direction(left: str, right: str) -> bool:
    return left.upper().strip() == right.upper().strip()


def evaluate_exposure(
    *,
    symbol: str,
    side: str,
    account_id: str,
    strategy_id: str,
    open_positions: list[dict[str, Any]],
    pending_signals: list[dict[str, Any]] | None = None,
    max_same_symbol_positions: int = 1,
    max_correlated_positions: int = 3,
) -> ExposureDecision:
    pending_signals = pending_signals or []
    reasons: list[str] = []
    normalized_symbol = symbol.upper().strip()
    normalized_side = side.upper().strip()
    currencies = set(currencies_for_symbol(normalized_symbol))
    same_symbol_count = 0
    related_count = 0

    for item in [*open_positions, *pending_signals]:
        item_symbol = str(item.get("symbol", "")).upper().strip()
        item_side = str(item.get("side", "")).upper().strip()
        item_account = str(item.get("account_id", account_id))
        item_strategy = str(item.get("strategy_id", ""))
        if item_account != account_id:
            continue
        if item_symbol == normalized_symbol and _same_direction(item_side, normalized_side):
            same_symbol_count += 1
            if item_strategy == strategy_id or not item_strategy:
                reasons.append("duplicate_same_symbol_direction")
        item_currencies = set(currencies_for_symbol(item_symbol))
        if currencies and currencies.intersection(item_currencies):
            related_count += 1

    if same_symbol_count >= max_same_symbol_positions:
        reasons.append("same_symbol_position_limit_reached")
    if related_count >= max_correlated_positions:
        reasons.append("correlation_exposure_limit_reached")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return ExposureDecision(
        duplicate_trade_risk=any(reason in unique_reasons for reason in ("duplicate_same_symbol_direction", "same_symbol_position_limit_reached")),
        correlation_exposure_ok="correlation_exposure_limit_reached" not in unique_reasons,
        reasons=unique_reasons,
        related_position_count=related_count,
    )
