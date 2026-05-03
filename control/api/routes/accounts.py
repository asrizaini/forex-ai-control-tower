from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import AccountCreate, AccountOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import Account
from ..permissions import has_permission

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_resource() -> dict:
    return {"module": "accounts", "description": "Account isolation and account-group management", "mode": "production-required"}


@router.get("/records", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.created_at.desc()).limit(200)))


@router.post("/records", response_model=AccountOut)
def create_account(payload: AccountCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> Account:
    if not has_permission(principal.role, "accounts:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    if payload.environment == "production-live":
        raise HTTPException(status_code=400, detail="production-live account creation requires dedicated governance workflow")
    account = Account(**payload.model_dump())
    db.add(account)
    audit(db, principal, "create", "account", payload.account_id, {"environment": payload.environment, "trading_mode": payload.trading_mode})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account already exists") from exc
    db.refresh(account)
    return account

