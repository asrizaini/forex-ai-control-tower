from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import StrategyApprovalOut, StrategyCreate, StrategyOut, StrategyPromoteRequest
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import PermissionAssignment, Strategy, StrategyApproval
from ..permissions import has_permission
from governance.strategy_governance import next_state_allowed, production_live_environment_allowed, required_gate_for_state
from strategies.registry import discover_plugins, plugin_metadata

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("")
def list_resource() -> dict:
    return {"module": "strategies", "description": "Strategy registry and lifecycle governance", "mode": "production-required"}


@router.get("/records", response_model=list[StrategyOut])
def list_strategies(db: Session = Depends(get_db)) -> list[Strategy]:
    return list(db.scalars(select(Strategy).order_by(Strategy.created_at.desc()).limit(200)))


@router.post("/records", response_model=StrategyOut)
def create_strategy(payload: StrategyCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> Strategy:
    if not has_permission(principal.role, "strategies:approve"):
        raise HTTPException(status_code=403, detail="Permission denied")
    if "production-live" in payload.allowed_environments:
        raise HTTPException(status_code=400, detail="production-live strategy access requires live governance approval")
    strategy = Strategy(**payload.model_dump(), live_approval_status="not_approved")
    db.add(strategy)
    audit(db, principal, "create", "strategy", payload.strategy_id, {"lifecycle_state": payload.lifecycle_state, "version": payload.version})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Strategy already exists") from exc
    db.refresh(strategy)
    return strategy


@router.get("/plugins")
def list_strategy_plugins() -> dict:
    return {"plugins": [plugin_metadata(plugin) for plugin in discover_plugins()]}


@router.post("/plugins/sync", response_model=list[StrategyOut])
def sync_strategy_plugins(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> list[Strategy]:
    if not has_permission(principal.role, "strategies:approve"):
        raise HTTPException(status_code=403, detail="Permission denied")
    synced: list[Strategy] = []
    for plugin in discover_plugins():
        existing = db.scalar(select(Strategy).where(Strategy.strategy_id == plugin.strategy_id).limit(1))
        metadata = plugin_metadata(plugin)
        if existing:
            existing.name = plugin.name
            existing.version = plugin.version
            existing.owner = plugin.owner
            existing.allowed_environments = list(plugin.allowed_environments)
            existing.metadata_json = metadata
            strategy = existing
        else:
            strategy = Strategy(
                strategy_id=plugin.strategy_id,
                name=plugin.name,
                version=plugin.version,
                owner=plugin.owner,
                lifecycle_state=plugin.lifecycle,
                allowed_environments=list(plugin.allowed_environments),
                live_approval_status="not_approved",
                metadata_json=metadata,
            )
            db.add(strategy)
        synced.append(strategy)
        audit(db, principal, "sync", "strategy_plugin", plugin.strategy_id, {"version": plugin.version, "lifecycle": plugin.lifecycle})
    db.commit()
    for strategy in synced:
        db.refresh(strategy)
    return synced


@router.post("/records/{strategy_id}/promote", response_model=StrategyOut)
def promote_strategy(
    strategy_id: str,
    payload: StrategyPromoteRequest,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> Strategy:
    if not has_permission(principal.role, "strategies:approve"):
        raise HTTPException(status_code=403, detail="Permission denied")
    strategy = db.scalar(select(Strategy).where(Strategy.strategy_id == strategy_id).limit(1))
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if not next_state_allowed(strategy.lifecycle_state, payload.target_state):
        raise HTTPException(status_code=400, detail="Strategy promotion must follow lifecycle order")
    gate = required_gate_for_state(payload.target_state)
    if payload.target_state == "approved_for_live_restricted" and principal.role != "super_admin":
        raise HTTPException(status_code=403, detail="Live restricted approval requires super_admin")
    strategy.lifecycle_state = payload.target_state
    if payload.target_state == "approved_for_live_restricted":
        strategy.live_approval_status = "approved" if payload.approve_production_live else "pending_live_governance"
        if production_live_environment_allowed(strategy.lifecycle_state, strategy.live_approval_status):
            strategy.allowed_environments = sorted(set([*strategy.allowed_environments, "production-live"]))
    approval = StrategyApproval(
        strategy_id=strategy.strategy_id,
        target_state=payload.target_state,
        approver=principal.user_id,
        gate=gate,
        notes=payload.notes,
        rollback_target=payload.rollback_target,
    )
    db.add(approval)
    audit(db, principal, "promote", "strategy", strategy.strategy_id, {"target_state": payload.target_state, "gate": gate})
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("/records/{strategy_id}/approvals", response_model=list[StrategyApprovalOut])
def strategy_approvals(strategy_id: str, db: Session = Depends(get_db)) -> list[StrategyApproval]:
    return list(db.scalars(select(StrategyApproval).where(StrategyApproval.strategy_id == strategy_id).order_by(StrategyApproval.created_at.desc()).limit(100)))


@router.post("/records/{strategy_id}/permissions", response_model=dict)
def grant_strategy_permission(
    strategy_id: str,
    payload: dict,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict:
    if not has_permission(principal.role, "strategies:approve"):
        raise HTTPException(status_code=403, detail="Permission denied")
    user_id = str(payload.get("user_id", "")).strip()
    account_id = str(payload.get("account_id", "")).strip() or None
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    db.add(PermissionAssignment(user_id=user_id, account_id=account_id, strategy_id=strategy_id, permission="strategy:use", enabled=True))
    audit(db, principal, "grant", "strategy_permission", strategy_id, {"user_id": user_id, "account_id": account_id})
    db.commit()
    return {"granted": True, "strategy_id": strategy_id, "user_id": user_id, "account_id": account_id}

