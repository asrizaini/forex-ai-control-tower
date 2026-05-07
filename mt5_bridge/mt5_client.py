from __future__ import annotations

import os
from typing import Any


class MT5Unavailable(RuntimeError):
    pass


def _json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class MT5Client:
    def __init__(self) -> None:
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise MT5Unavailable("MetaTrader5 Python package is not installed") from exc
        self.mt5 = mt5

    def connect(self) -> bool:
        terminal_path = os.getenv("MT5_TERMINAL_PATH")
        if terminal_path:
            return bool(self.mt5.initialize(path=terminal_path))
        return bool(self.mt5.initialize())

    def shutdown(self) -> None:
        self.mt5.shutdown()

    def require_connection(self) -> None:
        if not self.connect():
            raise MT5Unavailable(f"MT5 terminal is not connected: {self.mt5.last_error()}")

    def account_info(self) -> dict[str, Any]:
        self.require_connection()
        info = self.mt5.account_info()
        if info is None:
            raise MT5Unavailable(f"MT5 account unavailable: {self.mt5.last_error()}")
        return info._asdict()

    def symbols(self) -> list[str]:
        self.require_connection()
        symbols = self.mt5.symbols_get()
        return [symbol.name for symbol in symbols or ()]

    def symbol_info(self, symbol: str) -> dict[str, Any]:
        self.require_connection()
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise MT5Unavailable(f"MT5 symbol info unavailable for {symbol}: {self.mt5.last_error()}")
        return _json_safe(info._asdict())

    def _resolve_timeframe(self, timeframe: str | int | None) -> int:
        if timeframe is None:
            return self.mt5.TIMEFRAME_M1
        if isinstance(timeframe, int):
            return timeframe
        key = str(timeframe).strip().upper()
        mapping = {
            "M1": "TIMEFRAME_M1",
            "M5": "TIMEFRAME_M5",
            "M15": "TIMEFRAME_M15",
            "M30": "TIMEFRAME_M30",
            "H1": "TIMEFRAME_H1",
            "H4": "TIMEFRAME_H4",
            "D1": "TIMEFRAME_D1",
        }
        attr = mapping.get(key)
        if not attr:
            return self.mt5.TIMEFRAME_M1
        return int(getattr(self.mt5, attr, self.mt5.TIMEFRAME_M1))

    def rates(self, symbol: str, timeframe: str | int | None = None, count: int = 100) -> list[dict[str, Any]]:
        self.require_connection()
        tf = self._resolve_timeframe(timeframe)
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return []
        names = getattr(getattr(rates, "dtype", None), "names", None)
        if names:
            return [_json_safe({name: row[name] for name in names}) for row in rates]
        return [_json_safe(row) for row in rates.tolist()]

    def ticks(self, symbol: str) -> dict[str, Any]:
        self.require_connection()
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5Unavailable(f"MT5 tick unavailable for {symbol}: {self.mt5.last_error()}")
        return tick._asdict()

    def positions(self) -> list[dict[str, Any]]:
        self.require_connection()
        positions = self.mt5.positions_get()
        return [position._asdict() for position in positions or ()]

    def history(self) -> list[dict[str, Any]]:
        self.require_connection()
        deals = self.mt5.history_deals_get()
        return [deal._asdict() for deal in deals or ()]

    def order_check(self, request: dict[str, Any]) -> dict[str, Any]:
        self.require_connection()
        result = self.mt5.order_check(request)
        if result is None:
            raise MT5Unavailable(f"MT5 order_check failed: {self.mt5.last_error()}")
        return result._asdict()

    def order_send(self, request: dict[str, Any]) -> dict[str, Any]:
        self.require_connection()
        result = self.mt5.order_send(request)
        if result is None:
            raise MT5Unavailable(f"MT5 order_send failed: {self.mt5.last_error()}")
        return result._asdict()
