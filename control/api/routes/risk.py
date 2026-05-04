from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import current_principal
from ..auth import Principal
from ..control_schemas import ExecutionGuardCheckOut, ExecutionGuardCheckRequest, KillSwitchCreate, KillSwitchOut, RiskPolicyCreate, RiskPolicyOut
from ..crud import audit
from ..db import get_db
from ..models import Account, KillSwitch, RiskPolicy
from ..permissions import has_permission
from execution_guard.control_plane import ExecutionTelemetry, evaluate_control_plane_policy
from execution_guard.exposure import evaluate_exposure
from execution_guard.guard import approve_execution
from execution_guard.schemas import ExecutionRequest
from risk.kill_switch import active_kill_switch_exists, validate_scope

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("")
def list_resource() -> dict:
    return {"module": "risk", "description": "Risk status and kill-switch controls", "mode": "production-required"}


@router.post("/kill-switch", response_model=KillSwitchOut)
def kill_switch(payload: KillSwitchCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> KillSwitch:
    if not has_permission(principal.role, "system:halt"):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not validate_scope(payload.scope):
        raise HTTPException(status_code=400, detail="Invalid kill switch scope")
    if payload.scope in {"user", "account", "account_group", "strategy", "symbol"} and not payload.target_id:
        raise HTTPException(status_code=400, detail="target_id is required for scoped kill switch")
    record = KillSwitch(scope=payload.scope, target_id=payload.target_id, reason=payload.reason, created_by=principal.user_id)
    db.add(record)
    audit(db, principal, "activate", "kill_switch", f"{payload.scope}:{payload.target_id or '*'}", {"reason": payload.reason})
    db.commit()
    db.refresh(record)
    return record


@router.get("/kill-switches", response_model=list[KillSwitchOut])
def list_kill_switches(
    active_only: bool = True,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> list[KillSwitch]:
    statement = select(KillSwitch).order_by(KillSwitch.created_at.desc()).limit(200)
    if active_only:
        statement = select(KillSwitch).where(KillSwitch.active.is_(True)).order_by(KillSwitch.created_at.desc()).limit(200)
    return list(db.scalars(statement))


@router.post("/kill-switches/{kill_switch_id}/deactivate", response_model=KillSwitchOut)
def deactivate_kill_switch(
    kill_switch_id: int,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> KillSwitch:
    if not has_permission(principal.role, "system:halt"):
        raise HTTPException(status_code=403, detail="Permission denied")
    record = db.get(KillSwitch, kill_switch_id)
    if not record:
        raise HTTPException(status_code=404, detail="Kill switch not found")
    record.active = False
    record.deactivated_by = principal.user_id
    record.updated_at = datetime.utcnow()
    audit(db, principal, "deactivate", "kill_switch", str(kill_switch_id), {"scope": record.scope, "target_id": record.target_id})
    db.commit()
    db.refresh(record)
    return record


@router.get("/policies", response_model=list[RiskPolicyOut])
def list_risk_policies(db: Session = Depends(get_db)) -> list[RiskPolicy]:
    return list(db.scalars(select(RiskPolicy).order_by(RiskPolicy.created_at.desc()).limit(200)))


@router.post("/policies", response_model=RiskPolicyOut)
def create_risk_policy(payload: RiskPolicyCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> RiskPolicy:
    if not has_permission(principal.role, "risk:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    if payload.auto_execution_enabled:
        raise HTTPException(status_code=400, detail="Auto execution cannot be enabled through base risk policy API")
    policy = RiskPolicy(**payload.model_dump())
    db.add(policy)
    audit(db, principal, "create", "risk_policy", payload.scope, {"account_id": payload.account_id, "strategy_id": payload.strategy_id})
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/execution/check", response_model=ExecutionGuardCheckOut)
def check_execution_guard(
    payload: ExecutionGuardCheckRequest,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> ExecutionGuardCheckOut:
    account = db.scalar(select(Account).where(Account.account_id == payload.account_id).limit(1))
    db_kill_switch_active = active_kill_switch_exists(
        db,
        environment=account.environment if account else payload.environment,
        user_id=principal.user_id,
        account_id=payload.account_id,
        account_group=account.account_group if account else None,
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
    )
    request = ExecutionRequest(
        user_id=principal.user_id,
        account_id=payload.account_id,
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        side=payload.side,  # type: ignore[arg-type]
        volume=payload.volume,
        environment=payload.environment,
        trading_mode=payload.trading_mode,  # type: ignore[arg-type]
        live_order=payload.live_order,
        manual_approval=payload.manual_approval,
        order_check_passed=payload.order_check_passed,
        system_health_score=payload.system_health_score,
        kill_switch_active=payload.kill_switch_active or db_kill_switch_active,
    )
    exposure = evaluate_exposure(
        symbol=payload.symbol,
        side=payload.side,
        account_id=payload.account_id,
        strategy_id=payload.strategy_id,
        open_positions=payload.open_positions,
        pending_signals=payload.pending_signals,
        max_same_symbol_positions=payload.max_same_symbol_positions,
        max_correlated_positions=payload.max_correlated_positions,
    )
    telemetry = ExecutionTelemetry(
        daily_loss_pct=payload.daily_loss_pct,
        weekly_loss_pct=payload.weekly_loss_pct,
        open_trades=payload.open_trades,
        trades_today=payload.trades_today,
        spread_points=payload.spread_points,
        slippage_points=payload.slippage_points,
        market_data_quality_ok=payload.market_data_quality_ok,
        broker_compatibility_ok=payload.broker_compatibility_ok,
        margin_available=payload.margin_available,
        duplicate_trade_risk=payload.duplicate_trade_risk or exposure.duplicate_trade_risk,
        correlation_exposure_ok=payload.correlation_exposure_ok and exposure.correlation_exposure_ok,
        news_halt_active=payload.news_halt_active,
    )
    policy = evaluate_control_plane_policy(db, request, telemetry)
    guarded_request = ExecutionRequest(
        **{
            **request.__dict__,
            "environment": policy.effective_environment,
            "trading_mode": policy.effective_trading_mode,
            "checks": policy.checks,
        }
    )
    decision = approve_execution(guarded_request)
    audit(
        db,
        principal,
        "check",
        "execution_guard",
        f"{payload.account_id}:{payload.strategy_id}:{payload.symbol}",
        {
            "approved": decision.approved,
            "reasons": list(decision.reasons),
            "policy_reasons": list(policy.reasons),
            "exposure_reasons": list(exposure.reasons),
            "token_issued": bool(decision.token),
        },
    )
    db.commit()
    return ExecutionGuardCheckOut(
        approved=decision.approved,
        reasons=list(dict.fromkeys([*exposure.reasons, *policy.reasons, *decision.reasons])),
        token_issued=bool(decision.token),
        checks=policy.checks,
        effective_environment=policy.effective_environment,
        effective_trading_mode=policy.effective_trading_mode,
        policy_id=policy.policy_id,
    )

