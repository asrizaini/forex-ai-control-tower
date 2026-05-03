from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

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
    changelog: tuple[str, ...] = field(default_factory=tuple)
    supported_trade_styles: tuple[str, ...] = field(default_factory=tuple)
    supported_symbols: tuple[str, ...] = field(default_factory=tuple)
    supported_timeframes: tuple[str, ...] = field(default_factory=tuple)
    entry_rules: tuple[str, ...] = field(default_factory=tuple)
    exit_rules: tuple[str, ...] = field(default_factory=tuple)
    risk_rules: tuple[str, ...] = field(default_factory=tuple)
    news_behavior: str = "block_on_unknown_high_impact_news"
    allowed_users: tuple[str, ...] = field(default_factory=tuple)
    allowed_accounts: tuple[str, ...] = field(default_factory=tuple)
    allowed_environments: tuple[str, ...] = ("demo",)
    test_files: tuple[str, ...] = field(default_factory=tuple)
    rollback_target: str | None = None


def can_promote(plugin: StrategyPlugin, target: str) -> bool:
    return target in LIFECYCLE and LIFECYCLE.index(target) == LIFECYCLE.index(plugin.lifecycle) + 1


def plugin_root() -> Path:
    return Path(__file__).resolve().parent / "plugins"


def _tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    return tuple()


def load_plugin(path: Path) -> StrategyPlugin:
    data = json.loads(path.read_text(encoding="utf-8"))
    return StrategyPlugin(
        strategy_id=str(data["strategy_id"]),
        name=str(data["name"]),
        version=str(data.get("version", "0.1.0")),
        owner=str(data.get("owner", "system")),
        lifecycle=str(data.get("lifecycle", "draft")),
        changelog=_tuple(data.get("changelog", [])),
        supported_trade_styles=_tuple(data.get("supported_trade_styles", [])),
        supported_symbols=_tuple(data.get("supported_symbols", [])),
        supported_timeframes=_tuple(data.get("supported_timeframes", [])),
        entry_rules=_tuple(data.get("entry_rules", [])),
        exit_rules=_tuple(data.get("exit_rules", [])),
        risk_rules=_tuple(data.get("risk_rules", [])),
        news_behavior=str(data.get("news_behavior", "block_on_unknown_high_impact_news")),
        allowed_users=_tuple(data.get("allowed_users", [])),
        allowed_accounts=_tuple(data.get("allowed_accounts", [])),
        allowed_environments=_tuple(data.get("allowed_environments", ["demo"])),
        test_files=_tuple(data.get("test_files", [])),
        rollback_target=data.get("rollback_target"),
    )


def discover_plugins(root: Path | None = None) -> list[StrategyPlugin]:
    target = root or plugin_root()
    if not target.exists():
        return []
    return [load_plugin(path) for path in sorted(target.glob("*.json"))]


def plugin_metadata(plugin: StrategyPlugin) -> dict:
    data = asdict(plugin)
    for key, value in list(data.items()):
        if isinstance(value, tuple):
            data[key] = list(value)
    return data
