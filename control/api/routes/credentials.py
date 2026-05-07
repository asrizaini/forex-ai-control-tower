from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import CredentialReveal, CredentialUpdate
from ..credential_definitions import DEFINITION_BY_NAME, DEFINITIONS, generate_value
from ..credential_store import decrypt_value, get_config_value, migrate_runtime_credentials, public_status, sync_runtime_credentials, upsert_config
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import CredentialConfig

router = APIRouter(prefix="/credentials", tags=["credentials"])


def _require_admin(principal: Principal) -> None:
    if principal.role not in {"super_admin", "strategy_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin credentials access required")


@router.get("/catalog")
def catalog(principal: Principal = Depends(current_principal)) -> dict:
    _require_admin(principal)
    return {"credentials": [definition.public_dict() for definition in DEFINITIONS]}


@router.get("/status")
def status_view(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    _require_admin(principal)
    if sync_runtime_credentials(db):
        db.commit()
    items = public_status(db)
    missing_required = [item["name"] for item in items if item["required"] and not item["configured"]]
    invalid = [item["name"] for item in items if item["validation_status"] == "invalid"]
    return {
        "items": items,
        "configured_count": sum(1 for item in items if item["configured"]),
        "required_count": sum(1 for item in items if item["required"]),
        "missing_required": missing_required,
        "invalid": invalid,
        "healthy": not missing_required and not invalid,
        "notes": "Secret values are masked. Use explicit reveal only when necessary.",
    }


@router.post("/migrate-runtime")
def migrate_runtime(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    _require_admin(principal)
    migrated = migrate_runtime_credentials(db, principal.user_id)
    audit(
        db,
        principal,
        "credential_runtime_migrate",
        "credential_config",
        "runtime_to_db",
        {"migrated_count": len(migrated), "names": migrated, "value_logged": False},
    )
    db.commit()
    return {"status": "ok", "migrated_count": len(migrated), "migrated_names": migrated}


@router.put("/{name}")
def update_credential(
    name: str,
    payload: CredentialUpdate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_admin(principal)
    if name not in DEFINITION_BY_NAME:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown credential")
    record = upsert_config(db, name, payload.value, principal.user_id)
    audit(
        db,
        principal,
        "credential_update",
        "credential_config",
        name,
        {"configured": bool(payload.value), "sensitive": record.sensitive, "value_logged": False},
    )
    db.commit()
    return {
        "name": name,
        "configured": record.configured,
        "validation_status": record.validation_status,
        "validation_message": record.validation_message,
        "secret_value_returned": False,
    }


@router.post("/{name}/generate")
def generate_credential(name: str, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    _require_admin(principal)
    if name not in DEFINITION_BY_NAME:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown credential")
    value = generate_value(name)
    audit(db, principal, "credential_generate", "credential_config", name, {"stored": False, "value_logged": False})
    db.commit()
    return {"name": name, "value": value, "stored": False, "copy_now": True}


@router.post("/{name}/reveal")
def reveal_credential(
    name: str,
    payload: CredentialReveal,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_admin(principal)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Explicit confirmation required")
    if name not in DEFINITION_BY_NAME:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown credential")
    record = db.query(CredentialConfig).filter(CredentialConfig.name == name).one_or_none()
    value = decrypt_value(record.encrypted_value) if record and record.configured else get_config_value(db, name)
    if not value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential is not configured")
    source = "dashboard_store" if record and record.configured else "runtime_env"
    audit(db, principal, "credential_reveal", "credential_config", name, {"value_logged": False})
    db.commit()
    return {"name": name, "value": value, "sensitive": DEFINITION_BY_NAME[name].sensitive, "source": source}
