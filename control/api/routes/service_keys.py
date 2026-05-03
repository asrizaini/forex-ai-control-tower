from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import ServiceApiKeyCreate, ServiceApiKeyCreated, ServiceApiKeyOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import ServiceApiKey
from ..permissions import has_permission
from ..security import hash_token, random_token_urlsafe

router = APIRouter(prefix="/service-keys", tags=["service-keys"])


@router.get("", response_model=list[ServiceApiKeyOut])
def list_service_keys(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> list[ServiceApiKey]:
    if not has_permission(principal.role, "users:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    return list(db.scalars(select(ServiceApiKey).order_by(ServiceApiKey.created_at.desc()).limit(200)))


@router.post("", response_model=ServiceApiKeyCreated)
def create_service_key(payload: ServiceApiKeyCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> ServiceApiKeyCreated:
    if not has_permission(principal.role, "users:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    key_id = f"svc_{secrets.token_hex(6)}"
    api_key = f"{key_id}.{random_token_urlsafe(32)}"
    record = ServiceApiKey(
        key_id=key_id,
        name=payload.name,
        key_hash=hash_token(api_key),
        permissions=payload.permissions,
        created_by=principal.user_id,
    )
    db.add(record)
    audit(db, principal, "create", "service_api_key", key_id, {"name": payload.name, "permissions": payload.permissions})
    db.commit()
    db.refresh(record)
    data = ServiceApiKeyOut.model_validate(record).model_dump()
    data["api_key"] = api_key
    return ServiceApiKeyCreated(**data)


@router.post("/{key_id}/disable")
def disable_service_key(key_id: str, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    if not has_permission(principal.role, "users:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    record = db.scalar(select(ServiceApiKey).where(ServiceApiKey.key_id == key_id))
    if not record:
        raise HTTPException(status_code=404, detail="Service key not found")
    record.enabled = False
    audit(db, principal, "disable", "service_api_key", key_id, {})
    db.commit()
    return {"disabled": True}
