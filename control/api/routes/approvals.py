from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import TradeApprovalCreate, TradeApprovalDecision, TradeApprovalOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import TradeApproval
from ..permissions import has_permission
from ..time_utils import utcnow

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_resource() -> dict:
    return {"module": "approvals", "description": "Manual approval workflow", "mode": "production-required"}


def _approval_id() -> str:
    return f"approval_{secrets.token_hex(8)}"


def _can_approve(principal: Principal, approval: TradeApproval | None = None) -> bool:
    if has_permission(principal.role, "trades:approve"):
        return True
    return bool(approval and approval.user_id == principal.user_id and has_permission(principal.role, "trades:approve:self"))


@router.get("/requests", response_model=list[TradeApprovalOut])
def list_approval_requests(
    status: str | None = None,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> list[TradeApproval]:
    query = select(TradeApproval).order_by(TradeApproval.created_at.desc()).limit(200)
    if principal.role == "extended_user":
        query = select(TradeApproval).where(TradeApproval.user_id == principal.user_id).order_by(TradeApproval.created_at.desc()).limit(200)
    if status:
        base = select(TradeApproval).where(TradeApproval.status == status)
        if principal.role == "extended_user":
            base = base.where(TradeApproval.user_id == principal.user_id)
        query = base.order_by(TradeApproval.created_at.desc()).limit(200)
    return list(db.scalars(query))


@router.post("/requests", response_model=TradeApprovalOut)
def create_approval_request(
    payload: TradeApprovalCreate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> TradeApproval:
    if not has_permission(principal.role, "trades:approve") and not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    if payload.environment == "production-live":
        raise HTTPException(status_code=400, detail="production-live approval requires live-mode governance")
    approval = TradeApproval(
        approval_id=_approval_id(),
        user_id=payload.user_id,
        account_id=payload.account_id,
        strategy_id=payload.strategy_id,
        symbol=payload.symbol.upper(),
        side=payload.side,
        volume=payload.volume,
        environment=payload.environment,
        trading_mode=payload.trading_mode,
        requested_by=principal.user_id,
        reason=payload.reason,
        guard_check_json=payload.guard_check_json,
        expires_at=utcnow() + timedelta(minutes=payload.expires_minutes),
    )
    db.add(approval)
    audit(db, principal, "create", "trade_approval", approval.approval_id, {"account_id": payload.account_id, "strategy_id": payload.strategy_id})
    db.commit()
    db.refresh(approval)
    return approval


@router.post("/requests/{approval_id}/decision", response_model=TradeApprovalOut)
def decide_approval_request(
    approval_id: str,
    payload: TradeApprovalDecision,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> TradeApproval:
    approval = db.scalar(select(TradeApproval).where(TradeApproval.approval_id == approval_id))
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if not _can_approve(principal, approval):
        raise HTTPException(status_code=403, detail="Permission denied")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Approval request is not pending")
    if approval.expires_at and approval.expires_at < utcnow():
        approval.status = "expired"
        approval.updated_at = utcnow()
        db.commit()
        raise HTTPException(status_code=400, detail="Approval request expired")
    approval.status = payload.decision
    approval.decided_by = principal.user_id
    approval.reason = payload.reason or approval.reason
    approval.updated_at = utcnow()
    audit(db, principal, payload.decision, "trade_approval", approval_id, {"account_id": approval.account_id, "strategy_id": approval.strategy_id})
    db.commit()
    db.refresh(approval)
    return approval

