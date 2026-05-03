from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TradingMode = Literal[
    "monitor_only",
    "alert_only",
    "simulation",
    "paper_trade",
    "demo_auto",
    "manual_live",
    "restricted_live_auto",
    "emergency_halt",
]


@dataclass(frozen=True)
class ExecutionRequest:
    account_id: str
    strategy_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    volume: float
    user_id: str | None = None
    environment: str = "demo"
    trading_mode: TradingMode = "monitor_only"
    live_order: bool = False
    manual_approval: bool = False
    order_check_passed: bool = False
    system_health_score: int = 100
    kill_switch_active: bool = False
    checks: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class GuardDecision:
    approved: bool
    reasons: tuple[str, ...]
    token: str | None = None
