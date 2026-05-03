from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import ReleaseRecordCreate, ReleaseRecordOut, ReleaseStatusUpdate
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import ReleaseRecord
from ..permissions import has_permission

router = APIRouter(prefix="/deployments", tags=["deployments"])

LIVE_ENVIRONMENT = "production-live"


@router.get("")
def list_resource() -> dict:
    return {
        "module": "deployments",
        "description": "Deployment records, approvals, backup points, and rollback commands",
        "mode": "approval-required",
    }


def _deployment_id() -> str:
    return f"dep_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(4)}"


@router.get("/records", response_model=list[ReleaseRecordOut])
def list_records(environment: str | None = None, db: Session = Depends(get_db)) -> list[ReleaseRecord]:
    query = select(ReleaseRecord).order_by(ReleaseRecord.created_at.desc()).limit(200)
    if environment:
        query = select(ReleaseRecord).where(ReleaseRecord.environment == environment).order_by(ReleaseRecord.created_at.desc()).limit(200)
    return list(db.scalars(query))


@router.post("/records", response_model=ReleaseRecordOut)
def create_record(
    payload: ReleaseRecordCreate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> ReleaseRecord:
    if not has_permission(principal.role, "deployment:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    if payload.environment == LIVE_ENVIRONMENT and payload.test_result != "passed":
        raise HTTPException(status_code=400, detail="production-live deployment requires passed tests")
    record = ReleaseRecord(
        deployment_id=_deployment_id(),
        version=payload.version,
        environment=payload.environment,
        status="approved" if payload.environment != LIVE_ENVIRONMENT else "planned",
        changelog=payload.changelog,
        backup_point=payload.backup_point,
        test_result=payload.test_result,
        approver=payload.approver,
        rollback_command=payload.rollback_command,
        rollback_target=payload.rollback_target,
        metadata_json=payload.metadata_json,
        created_by=principal.user_id,
    )
    db.add(record)
    audit(db, principal, "create", "deployment_record", record.deployment_id, {"environment": payload.environment, "version": payload.version})
    db.commit()
    db.refresh(record)
    return record


@router.post("/records/{deployment_id}/status", response_model=ReleaseRecordOut)
def update_status(
    deployment_id: str,
    payload: ReleaseStatusUpdate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> ReleaseRecord:
    if not has_permission(principal.role, "deployment:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    record = db.scalar(select(ReleaseRecord).where(ReleaseRecord.deployment_id == deployment_id))
    if not record:
        raise HTTPException(status_code=404, detail="Deployment record not found")
    if payload.status == "deployed" and record.environment == LIVE_ENVIRONMENT and record.status != "approved":
        raise HTTPException(status_code=400, detail="production-live deployment must be approved before deployed")
    record.status = payload.status
    if payload.test_result:
        record.test_result = payload.test_result
    record.updated_at = datetime.utcnow()
    audit(db, principal, "update", "deployment_record", deployment_id, {"status": payload.status, "notes": payload.notes})
    db.commit()
    db.refresh(record)
    return record


@router.get("/records/{deployment_id}/rollback")
def rollback_plan(deployment_id: str, db: Session = Depends(get_db)) -> dict:
    record = db.scalar(select(ReleaseRecord).where(ReleaseRecord.deployment_id == deployment_id))
    if not record:
        raise HTTPException(status_code=404, detail="Deployment record not found")
    return {
        "deployment_id": deployment_id,
        "rollback_available": bool(record.rollback_command),
        "rollback_target": record.rollback_target,
        "rollback_command": record.rollback_command,
        "backup_point": record.backup_point,
        "requires_admin_execution": True,
    }
