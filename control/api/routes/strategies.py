from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import StrategyCreate, StrategyOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import Strategy
from ..permissions import has_permission

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

