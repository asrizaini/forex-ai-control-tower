from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import current_principal
from ..auth import Principal
from ..control_schemas import RiskPolicyCreate, RiskPolicyOut
from ..crud import audit
from ..db import get_db
from ..models import RiskPolicy
from ..permissions import has_permission

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

