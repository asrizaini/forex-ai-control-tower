from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .auth import Principal
from .models import AuditLog


def audit(db: Session, principal: Principal | None, action: str, resource_type: str, resource_id: str, details: dict[str, Any] | None = None) -> None:
    actor = principal.user_id if principal else "system"
    db.add(
        AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            note="append-only audit event",
        )
    )
