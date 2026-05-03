from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import PermissionCreate, PermissionOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import PermissionAssignment
from ..permissions import has_permission

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=list[PermissionOut])
def list_permissions(db: Session = Depends(get_db)) -> list[PermissionAssignment]:
    return list(db.scalars(select(PermissionAssignment).order_by(PermissionAssignment.created_at.desc()).limit(200)))


@router.post("", response_model=PermissionOut)
def create_permission(payload: PermissionCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> PermissionAssignment:
    if not has_permission(principal.role, "users:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    assignment = PermissionAssignment(**payload.model_dump())
    db.add(assignment)
    audit(db, principal, "create", "permission", payload.user_id, payload.model_dump())
    db.commit()
    db.refresh(assignment)
    return assignment
