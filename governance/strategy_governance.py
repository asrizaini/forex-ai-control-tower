from __future__ import annotations

from strategies.registry import LIFECYCLE


LIVE_STATES = {"approved_for_live_restricted"}
DEMO_AUTO_STATES = {"approved_for_demo_auto"}


def next_state_allowed(current: str, target: str) -> bool:
    if current not in LIFECYCLE or target not in LIFECYCLE:
        return False
    return LIFECYCLE.index(target) == LIFECYCLE.index(current) + 1


def required_gate_for_state(target: str) -> str:
    if target == "backtesting":
        return "strategy_admin"
    if target == "forward_testing":
        return "backtest_passed"
    if target == "paper_trading":
        return "forward_test_passed"
    if target == "demo_testing":
        return "paper_trade_review_passed"
    if target == "approved_for_manual":
        return "manual_strategy_approval"
    if target == "approved_for_demo_auto":
        return "demo_validation_passed"
    if target == "approved_for_live_restricted":
        return "live_governance_approval"
    return "draft"


def production_live_environment_allowed(lifecycle_state: str, live_approval_status: str) -> bool:
    return lifecycle_state in LIVE_STATES and live_approval_status == "approved"
