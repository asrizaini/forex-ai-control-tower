from __future__ import annotations

import secrets
import urllib.error
import urllib.parse
import urllib.request
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
from ..time_utils import to_local
from localization.locale_manager import normalize_language
from notifications.hub import ESCALATION, channel_status, route_notification
from ..credential_store import get_config_value

router = APIRouter(prefix="/notifications", tags=["notifications"])

PRIVATE_ALERT_NETWORKS = (
    ip_network("10.10.1.0/24"),
    ip_network("127.0.0.0/8"),
)


def _configured_secret(db: Session, name: str) -> str | None:
    try:
        return get_config_value(db, name)
    except Exception:
        return None


def _as_notification_out(event: NotificationEvent) -> NotificationOut:
    created = event.created_at
    return NotificationOut(
        id=event.id,
        event_id=event.event_id,
        level=event.level,
        notification_type=event.notification_type,
        user_id=event.user_id,
        account_id=event.account_id,
        title=event.title,
        message=event.message,
        language=event.language,
        routed_channels=event.routed_channels,
        pending_channels=event.pending_channels,
        status=event.status,
        metadata_json=event.metadata_json,
        created_at=to_local(created) if created else to_local(),
    )


def _send_telegram(db: Session, title: str, message: str) -> dict:
    token = _configured_secret(db, "TELEGRAM_BOT_TOKEN")
    chat_id = _configured_secret(db, "TELEGRAM_ADMIN_CHAT_ID")
    if not token or not chat_id:
        return {"ok": False, "reason": "telegram_credentials_missing"}
    text = f"{title}\n{message}"[:3900]
    body = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            import json

            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            import json

            body = json.loads(exc.read().decode("utf-8", errors="replace"))
            detail = str(body.get("description", "")) if isinstance(body, dict) else ""
        except Exception:
            detail = ""
        return {"ok": False, "reason": f"HTTPError:{exc.code}", "detail": detail}
    except Exception as exc:
        return {"ok": False, "reason": type(exc).__name__}
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    return {
        "ok": bool(payload.get("ok")) if isinstance(payload, dict) else False,
        "message_id": result.get("message_id"),
    }


def _deliver_notification(db: Session, routed_channels: list[str], title: str, message: str) -> tuple[list[str], list[str], dict]:
    delivered: list[str] = []
    failed: list[str] = []
    results: dict = {}
    for channel in routed_channels:
        if channel == "dashboard":
            delivered.append(channel)
            results[channel] = {"ok": True, "reason": "dashboard_recorded"}
            continue
        if channel == "telegram":
            result = _send_telegram(db, title, message)
            if result.get("ok"):
                delivered.append(channel)
            else:
                failed.append(channel)
            results[channel] = result
            continue
        failed.append(channel)
        results[channel] = {"ok": False, "reason": "adapter_not_implemented"}
    return delivered, failed, results


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
    rows = list(db.scalars(select(NotificationEvent).order_by(NotificationEvent.created_at.desc()).limit(200)))
    return [_as_notification_out(item) for item in rows]


@router.post("/events", response_model=NotificationOut)
def create_event(
    payload: NotificationCreate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> NotificationOut:
    routing = route_notification(payload.level, payload.quiet_hours_enabled)
    delivered, failed, delivery_result = _deliver_notification(db, routing["routed_channels"], payload.title, payload.message)
    final_status = "pending_channel_configuration"
    if routing["routed_channels"]:
        if delivered and not failed:
            final_status = "sent"
        elif delivered and failed:
            final_status = "partial_delivery"
        else:
            final_status = "delivery_failed"
    event = NotificationEvent(
        event_id=f"ntf_{secrets.token_hex(8)}",
        level=payload.level,
        notification_type=payload.notification_type,
        user_id=payload.user_id,
        account_id=payload.account_id,
        title=payload.title,
        message=payload.message,
        language=normalize_language(payload.language),
        routed_channels=delivered,
        pending_channels=sorted(set(routing["pending_channels"] + failed)),
        status=final_status,
        metadata_json={**payload.metadata_json, "routing": routing, "delivery": delivery_result},
    )
    db.add(event)
    audit(db, principal, "create", "notification_event", event.event_id, {"level": payload.level, "channels": routing["routed_channels"]})
    db.commit()
    db.refresh(event)
    return _as_notification_out(event)


def _alert_webhook_allowed(request: Request, x_alertmanager_token: str | None, db: Session) -> bool:
    expected = _configured_secret(db, "ALERTMANAGER_WEBHOOK_TOKEN")
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
    if not _alert_webhook_allowed(request, x_alertmanager_token, db):
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
        title = str(annotations.get("summary") or labels.get("alertname") or "Monitoring alert")
        message = str(annotations.get("description") or status_value)
        delivered, failed, delivery_result = _deliver_notification(db, routing["routed_channels"], title, message)
        final_status = "pending_channel_configuration"
        if routing["routed_channels"]:
            if delivered and not failed:
                final_status = "sent"
            elif delivered and failed:
                final_status = "partial_delivery"
            else:
                final_status = "delivery_failed"
        event = NotificationEvent(
            event_id=f"ntf_{secrets.token_hex(8)}",
            level=level,
            notification_type="system_alert",
            title=title,
            message=message,
            language="en",
            routed_channels=delivered,
            pending_channels=sorted(set(routing["pending_channels"] + failed)),
            status=final_status,
            metadata_json={
                "source": "alertmanager",
                "labels": labels,
                "annotations": annotations,
                "alert_status": status_value,
                "routing": routing,
                "delivery": delivery_result,
            },
        )
        db.add(event)
        audit(db, None, "ingest", "monitoring_alert", event.event_id, {"alertname": labels.get("alertname"), "severity": labels.get("severity")})
        created += 1
    db.commit()
    return {"accepted": True, "events_created": created}

