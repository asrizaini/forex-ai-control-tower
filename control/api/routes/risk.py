from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import current_principal
from ..auth import Principal
from ..control_schemas import ExecutionGuardCheckOut, ExecutionGuardCheckRequest, RiskPolicyCreate, RiskPolicyOut
from ..crud import audit
from ..db import get_db
from ..models import RiskPolicy
from ..permissions import has_permission
from execution_guard.control_plane import ExecutionTelemetry, evaluate_control_plane_policy
from execution_guard.guard import approve_execution
from execution_guard.schemas import ExecutionRequest

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("")
def list_resource() -> dict:
    return {"module": "risk", "description": "Risk status and kill-switch controls", "mode": "production-required"}


@router.post("/kill-switch")
def kill_switch(payload: dict, principal: Principal = Depends(current_principal)) -> dict:
    if not has_permission(principal.role, "system:halt"):
        raise HTTPException(status_code=403, detail="Permission denied")
    return {"halt_scope": payload.get("scope", "all_execution"), "active": True, "overrides_agents": True}


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
        kill_switch_active=payload.kill_switch_active,
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
        duplicate_trade_risk=payload.duplicate_trade_risk,
        correlation_exposure_ok=payload.correlation_exposure_ok,
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
        {"approved": decision.approved, "reasons": list(decision.reasons), "policy_reasons": list(policy.reasons), "token_issued": bool(decision.token)},
    )
    db.commit()
    return ExecutionGuardCheckOut(
        approved=decision.approved,
        reasons=list(dict.fromkeys([*policy.reasons, *decision.reasons])),
        token_issued=bool(decision.token),
        checks=policy.checks,
        effective_environment=policy.effective_environment,
        effective_trading_mode=policy.effective_trading_mode,
        policy_id=policy.policy_id,
    )

