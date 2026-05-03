from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import NotificationCreate, NotificationOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import NotificationEvent
from localization.locale_manager import normalize_language
from notifications.hub import ESCALATION, channel_status, route_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_resource() -> dict:
    return {"module": "notifications", "description": "Notification preferences and routing", "mode": "production-required"}


@router.get("/escalation")
def escalation() -> dict:
    return {"escalation": ESCALATION}


@router.get("/channels/status")
def channels_status() -> dict:
    return {"channels": channel_status()}


@router.get("/events", response_model=list[NotificationOut])
def list_events(db: Session = Depends(get_db)) -> list[NotificationEvent]:
    return list(db.scalars(select(NotificationEvent).order_by(NotificationEvent.created_at.desc()).limit(200)))


@router.post("/events", response_model=NotificationOut)
def create_event(
    payload: NotificationCreate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> NotificationEvent:
    routing = route_notification(payload.level, payload.quiet_hours_enabled)
    event = NotificationEvent(
        event_id=f"ntf_{secrets.token_hex(8)}",
        level=payload.level,
        notification_type=payload.notification_type,
        user_id=payload.user_id,
        account_id=payload.account_id,
        title=payload.title,
        message=payload.message,
        language=normalize_language(payload.language),
        routed_channels=routing["routed_channels"],
        pending_channels=routing["pending_channels"],
        status="queued" if routing["routed_channels"] else "pending_channel_configuration",
        metadata_json={**payload.metadata_json, "routing": routing},
    )
    db.add(event)
    audit(db, principal, "create", "notification_event", event.event_id, {"level": payload.level, "channels": routing["routed_channels"]})
    db.commit()
    db.refresh(event)
    return event

