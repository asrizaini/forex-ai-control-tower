from __future__ import annotations

from typing import Any


class MT5Unavailable(RuntimeError):
    pass


class MT5Client:
    def __init__(self) -> None:
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise MT5Unavailable("MetaTrader5 Python package is not installed") from exc
        self.mt5 = mt5

    def connect(self) -> bool:
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

    def rates(self, symbol: str, timeframe: int | None = None, count: int = 100) -> list[dict[str, Any]]:
        self.require_connection()
        tf = timeframe or self.mt5.TIMEFRAME_M1
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        return [] if rates is None else [dict(row) for row in rates.tolist()]

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
