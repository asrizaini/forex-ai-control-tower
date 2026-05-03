from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from control.api.models import Account, PermissionAssignment, RiskPolicy, Strategy, User

from .schemas import ExecutionRequest


TRADE_PERMISSIONS = {"trades:approve", "trades:execute", "trades:execute:demo"}
ACCOUNT_PERMISSIONS = {"account:trade", "trades:approve", "trades:execute", "trades:execute:demo"}
STRATEGY_PERMISSIONS = {"strategy:use", "trades:approve", "trades:execute", "trades:execute:demo"}
EXECUTION_TRADING_MODES = {"simulation", "paper_trade", "demo_auto", "manual_live", "restricted_live_auto"}


@dataclass(frozen=True)
class ExecutionTelemetry:
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    open_trades: int = 0
    trades_today: int = 0
    spread_points: float | None = None
    slippage_points: float | None = None
    market_data_quality_ok: bool = False
    broker_compatibility_ok: bool = False
    margin_available: bool = False
    duplicate_trade_risk: bool = True
    correlation_exposure_ok: bool = False
    news_halt_active: bool = True


@dataclass(frozen=True)
class ControlPlaneGuardResult:
    checks: dict[str, bool]
    reasons: tuple[str, ...]
    effective_environment: str
    effective_trading_mode: str
    policy_id: int | None


def _enabled_permission_exists(
    db: Session,
    user_id: str,
    allowed: set[str],
    account_id: str | None = None,
    strategy_id: str | None = None,
) -> bool:
    filters = [
        PermissionAssignment.user_id == user_id,
        PermissionAssignment.enabled.is_(True),
        PermissionAssignment.permission.in_(allowed),
    ]
    if account_id is not None:
        filters.append(PermissionAssignment.account_id == account_id)
    if strategy_id is not None:
        filters.append(PermissionAssignment.strategy_id == strategy_id)
    return db.scalar(select(PermissionAssignment.id).where(and_(*filters)).limit(1)) is not None


def _select_policy(db: Session, account_id: str, strategy_id: str) -> RiskPolicy | None:
    return db.scalar(
        select(RiskPolicy)
        .where(
            or_(
                and_(RiskPolicy.account_id == account_id, RiskPolicy.strategy_id == strategy_id),
                and_(RiskPolicy.account_id == account_id, RiskPolicy.strategy_id.is_(None)),
                and_(RiskPolicy.account_id.is_(None), RiskPolicy.strategy_id == strategy_id),
                and_(RiskPolicy.scope == "global", RiskPolicy.account_id.is_(None), RiskPolicy.strategy_id.is_(None)),
            )
        )
        .order_by(
            RiskPolicy.account_id.desc().nulls_last(),
            RiskPolicy.strategy_id.desc().nulls_last(),
            RiskPolicy.created_at.desc(),
        )
        .limit(1)
    )


def evaluate_control_plane_policy(
    db: Session,
    request: ExecutionRequest,
    telemetry: ExecutionTelemetry,
) -> ControlPlaneGuardResult:
    reasons: list[str] = []
    user = db.scalar(select(User).where(User.user_id == request.user_id).limit(1)) if request.user_id else None
    account = db.scalar(select(Account).where(Account.account_id == request.account_id).limit(1))
    strategy = db.scalar(select(Strategy).where(Strategy.strategy_id == request.strategy_id).limit(1))
    policy = _select_policy(db, request.account_id, request.strategy_id)

    user_permission = bool(user and user.enabled and _enabled_permission_exists(db, user.user_id, TRADE_PERMISSIONS))
    account_permission = bool(
        user
        and account
        and account.enabled
        and _enabled_permission_exists(db, user.user_id, ACCOUNT_PERMISSIONS, account_id=account.account_id)
    )
    strategy_permission = bool(
        user
        and strategy
        and _enabled_permission_exists(db, user.user_id, STRATEGY_PERMISSIONS, strategy_id=strategy.strategy_id)
    )

    effective_environment = account.environment if account else request.environment
    effective_trading_mode = account.trading_mode if account else request.trading_mode
    strategy_environment_ok = bool(strategy and effective_environment in (strategy.allowed_environments or []))
    trading_mode_ok = bool(
        account
        and account.enabled
        and effective_trading_mode in EXECUTION_TRADING_MODES
        and effective_trading_mode == request.trading_mode
    )

    risk_limits_ok = True
    spread_limit_ok = telemetry.spread_points is not None
    slippage_limit_ok = telemetry.slippage_points is not None
    if policy:
        if policy.max_daily_loss_pct and telemetry.daily_loss_pct >= policy.max_daily_loss_pct:
            risk_limits_ok = False
            reasons.append("max_daily_loss_reached")
        if policy.max_weekly_loss_pct and telemetry.weekly_loss_pct >= policy.max_weekly_loss_pct:
            risk_limits_ok = False
            reasons.append("max_weekly_loss_reached")
        if policy.max_open_trades and telemetry.open_trades >= policy.max_open_trades:
            risk_limits_ok = False
            reasons.append("max_open_trades_reached")
        if policy.max_trades_per_day and telemetry.trades_today >= policy.max_trades_per_day:
            risk_limits_ok = False
            reasons.append("max_trades_per_day_reached")
        if policy.max_spread_points:
            spread_limit_ok = telemetry.spread_points is not None and telemetry.spread_points <= policy.max_spread_points
            if not spread_limit_ok:
                reasons.append("spread_limit_exceeded_or_missing")
        max_slippage = float((policy.metadata_json or {}).get("max_slippage_points", 0.0) or 0.0)
        if max_slippage:
            slippage_limit_ok = telemetry.slippage_points is not None and telemetry.slippage_points <= max_slippage
            if not slippage_limit_ok:
                reasons.append("slippage_limit_exceeded_or_missing")
    else:
        risk_limits_ok = False
        reasons.append("risk_policy_missing")

    checks = {
        "user_permission": user_permission,
        "account_permission": account_permission,
        "strategy_permission": strategy_permission and strategy_environment_ok,
        "risk_limits": risk_limits_ok,
        "spread_limit": spread_limit_ok,
        "slippage_limit": slippage_limit_ok,
        "market_data_quality": telemetry.market_data_quality_ok,
        "broker_compatibility": telemetry.broker_compatibility_ok,
        "margin_availability": telemetry.margin_available,
        "duplicate_trade_risk": not telemetry.duplicate_trade_risk,
        "correlation_exposure": telemetry.correlation_exposure_ok,
        "news_halt": not telemetry.news_halt_active,
        "trading_mode_policy": trading_mode_ok,
    }
    for name, passed in checks.items():
        if not passed and name not in {"risk_limits", "spread_limit", "slippage_limit"}:
            reasons.append(f"{name}_failed")
    if not strategy_environment_ok:
        reasons.append("strategy_environment_not_allowed")
    return ControlPlaneGuardResult(
        checks=checks,
        reasons=tuple(dict.fromkeys(reasons)),
        effective_environment=effective_environment,
        effective_trading_mode=effective_trading_mode,
        policy_id=policy.id if policy else None,
    )
