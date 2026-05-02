from __future__ import annotations

from dataclasses import dataclass, field

LIFECYCLE = (
    "draft",
    "backtesting",
    "forward_testing",
    "paper_trading",
    "demo_testing",
    "approved_for_manual",
    "approved_for_demo_auto",
    "approved_for_live_restricted",
)


@dataclass(frozen=True)
class StrategyPlugin:
    strategy_id: str
    name: str
    version: str
    owner: str
    lifecycle: str = "draft"
    allowed_users: tuple[str, ...] = field(default_factory=tuple)
    allowed_accounts: tuple[str, ...] = field(default_factory=tuple)
    allowed_environments: tuple[str, ...] = ("demo",)


def can_promote(plugin: StrategyPlugin, target: str) -> bool:
    return target in LIFECYCLE and LIFECYCLE.index(target) >= LIFECYCLE.index(plugin.lifecycle)
