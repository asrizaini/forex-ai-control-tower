from __future__ import annotations

import secrets
from ipaddress import ip_address, ip_network

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
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

PRIVATE_ALERT_NETWORKS = (
    ip_network("10.10.1.0/24"),
    ip_network("127.0.0.0/8"),
)


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


def _alert_webhook_allowed(request: Request, x_alertmanager_token: str | None) -> bool:
    import os

    expected = os.getenv("ALERTMANAGER_WEBHOOK_TOKEN")
    if expected:
        return bool(x_alertmanager_token) and x_alertmanager_token == expected
    client_host = request.client.host if request.client else ""
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    return any(client_ip in network for network in PRIVATE_ALERT_NETWORKS)


@router.post("/monitoring/webhook", status_code=status.HTTP_202_ACCEPTED)
def monitoring_webhook(
    payload: dict,
    request: Request,
    x_alertmanager_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not _alert_webhook_allowed(request, x_alertmanager_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Monitoring webhook is restricted")
    alerts = payload.get("alerts", []) if isinstance(payload, dict) else []
    created = 0
    for alert in alerts if isinstance(alerts, list) else []:
        if not isinstance(alert, dict):
            continue
        labels = alert.get("labels", {}) if isinstance(alert.get("labels"), dict) else {}
        annotations = alert.get("annotations", {}) if isinstance(alert.get("annotations"), dict) else {}
        status_value = str(alert.get("status", "firing"))
        level = "critical" if labels.get("severity") in {"critical", "emergency"} else "warning"
        routing = route_notification(level)
        event = NotificationEvent(
            event_id=f"ntf_{secrets.token_hex(8)}",
            level=level,
            notification_type="system_alert",
            title=str(annotations.get("summary") or labels.get("alertname") or "Monitoring alert"),
            message=str(annotations.get("description") or status_value),
            language="en",
            routed_channels=routing["routed_channels"],
            pending_channels=routing["pending_channels"],
            status="queued" if routing["routed_channels"] else "pending_channel_configuration",
            metadata_json={"source": "alertmanager", "labels": labels, "annotations": annotations, "alert_status": status_value, "routing": routing},
        )
        db.add(event)
        audit(db, None, "ingest", "monitoring_alert", event.event_id, {"alertname": labels.get("alertname"), "severity": labels.get("severity")})
        created += 1
    db.commit()
    return {"accepted": True, "events_created": created}

