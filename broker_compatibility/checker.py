from __future__ import annotations

from typing import Any


def check_broker_profile(profile: dict) -> tuple[bool, str]:
    required = {"symbols", "min_lot", "max_lot", "lot_step", "execution_mode"}
    missing = required - set(profile)
    if missing:
        return False, f"missing broker profile fields: {sorted(missing)}"
    return True, "broker profile accepted"


def check_symbol_metadata(symbol: str, info: dict[str, Any], *, min_volume: float = 0.01) -> dict[str, Any]:
    volume_min = _float(info.get("volume_min"))
    volume_max = _float(info.get("volume_max"))
    volume_step = _float(info.get("volume_step"))
    trade_mode = _int(info.get("trade_mode"))
    trade_contract_size = _float(info.get("trade_contract_size"))
    visible = bool(info.get("visible"))
    selected = bool(info.get("select"))

    checks = {
        "symbol_available": bool(info.get("name") or symbol),
        "selected": selected,
        "visible_or_selected": visible or selected,
        "volume_min_ok": volume_min is not None and volume_min <= min_volume,
        "volume_max_ok": volume_max is not None and volume_max >= min_volume,
        "volume_step_ok": volume_step is not None and 0 < volume_step <= min_volume,
        "trade_mode_known": trade_mode is not None,
        "contract_size_known": trade_contract_size is not None and trade_contract_size > 0,
    }
    passed = all(checks.values())
    return {
        "symbol": symbol.upper(),
        "passed": passed,
        "checks": checks,
        "metadata": {
            "volume_min": volume_min,
            "volume_max": volume_max,
            "volume_step": volume_step,
            "trade_mode": trade_mode,
            "trade_contract_size": trade_contract_size,
            "trade_stops_level": _int(info.get("trade_stops_level")),
            "trade_freeze_level": _int(info.get("trade_freeze_level")),
            "digits": _int(info.get("digits")),
            "spread": _float(info.get("spread")),
        },
    }


def summarize_broker_compatibility(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed_symbols = [item["symbol"] for item in results if item.get("passed")]
    failed_symbols = [item["symbol"] for item in results if not item.get("passed")]
    return {
        "passed": bool(results) and not failed_symbols,
        "symbols_checked": len(results),
        "passed_symbols": passed_symbols,
        "failed_symbols": failed_symbols,
        "results": results,
    }


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
