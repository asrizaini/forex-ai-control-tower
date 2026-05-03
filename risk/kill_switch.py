from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from control.api.models import KillSwitch

SCOPES = {
    "all_live",
    "all_demo",
    "user",
    "account",
    "account_group",
    "strategy",
    "symbol",
    "news_trading",
    "auto_execution",
    "execution_only",
}

GLOBAL_SCOPES = {"auto_execution", "execution_only", "news_trading"}


def validate_scope(scope: str) -> bool:
    return scope in SCOPES


def active_kill_switch_exists(
    db: Session,
    *,
    environment: str,
    user_id: str | None = None,
    account_id: str | None = None,
    account_group: str | None = None,
    strategy_id: str | None = None,
    symbol: str | None = None,
) -> bool:
    clauses = [
        and_(KillSwitch.scope.in_(GLOBAL_SCOPES), KillSwitch.target_id.is_(None)),
    ]
    if environment == "production-live":
        clauses.append(and_(KillSwitch.scope == "all_live", KillSwitch.target_id.is_(None)))
    if environment == "demo":
        clauses.append(and_(KillSwitch.scope == "all_demo", KillSwitch.target_id.is_(None)))
    if user_id:
        clauses.append(and_(KillSwitch.scope == "user", KillSwitch.target_id == user_id))
    if account_id:
        clauses.append(and_(KillSwitch.scope == "account", KillSwitch.target_id == account_id))
    if account_group:
        clauses.append(and_(KillSwitch.scope == "account_group", KillSwitch.target_id == account_group))
    if strategy_id:
        clauses.append(and_(KillSwitch.scope == "strategy", KillSwitch.target_id == strategy_id))
    if symbol:
        clauses.append(and_(KillSwitch.scope == "symbol", KillSwitch.target_id == symbol))
    return db.scalar(select(KillSwitch.id).where(KillSwitch.active.is_(True), or_(*clauses)).limit(1)) is not None
