from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import UserCreate, UserOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import User
from ..permissions import has_permission

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_resource() -> dict:
    return {"module": "users", "description": "User management uses deny-by-default RBAC", "mode": "production-required"}


@router.get("/records", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc()).limit(200)))


@router.post("/records", response_model=UserOut)
def create_user(payload: UserCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> User:
    if not has_permission(principal.role, "users:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    user = User(**payload.model_dump())
    db.add(user)
    audit(db, principal, "create", "user", payload.user_id, {"role": payload.role, "language": payload.language})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists") from exc
    db.refresh(user)
    return user

