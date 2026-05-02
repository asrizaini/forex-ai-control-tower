from __future__ import annotations

from .schemas import ExecutionRequest


REQUIRED_CHECKS = (
    "account_permission",
    "user_permission",
    "strategy_permission",
    "risk_limits",
    "spread_limit",
    "market_data_quality",
    "broker_compatibility",
)


def evaluate_required_checks(request: ExecutionRequest) -> list[str]:
    failed = [name for name in REQUIRED_CHECKS if not request.checks.get(name, False)]
    if request.kill_switch_active:
        failed.append("kill_switch_active")
    if request.system_health_score < 70:
        failed.append("system_health_below_execution_threshold")
    if request.live_order and request.environment != "production-live":
        failed.append("live_order_environment_mismatch")
    if request.live_order and not request.manual_approval:
        failed.append("manual_live_approval_required")
    if request.trading_mode in {"monitor_only", "alert_only", "emergency_halt"}:
        failed.append(f"trading_mode_blocks_execution:{request.trading_mode}")
    return failed
