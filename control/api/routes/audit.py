from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import AuditLogOut
from ..db import get_db
from ..dependencies import current_principal
from ..models import AuditLog
from ..permissions import has_permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogOut])
def list_audit_logs(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> list[AuditLog]:
    if not has_permission(principal.role, "audit:read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    return list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)))
