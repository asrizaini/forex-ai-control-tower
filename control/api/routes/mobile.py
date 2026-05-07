from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import MobilePushRegisterRequest, MobilePushRegistrationOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import Account, AccountSnapshot, MobilePushRegistration, NotificationEvent, PermissionAssignment, TradeApproval
from ..time_utils import utcnow, iso_local

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("")
def list_resource() -> dict:
    return {"module": "mobile", "description": "Mobile bootstrap and push registration", "mode": "production-required"}


@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db)) -> dict:
    latest_account = db.scalar(select(AccountSnapshot).order_by(AccountSnapshot.created_at.desc()).limit(1))
    accounts_count = db.scalar(select(func.count()).select_from(Account)) or 0
    return {
        "environment": "demo",
        "trading_mode": "monitor_only",
        "live_auto_trading": False,
        "language_modes": ["en", "ms-MY", "auto"],
        "auth": {"jwt": True, "refresh_tokens": True, "two_factor": True},
        "websocket_paths": [
            "/ws/v1/system",
            "/ws/v1/signals",
            "/ws/v1/trades",
            "/ws/v1/approvals",
            "/ws/v1/risk",
            "/ws/v1/agent-theater",
            "/ws/v1/accounts/{account_id}",
            "/ws/v1/users/{user_id}",
        ],
        "features": {
            "account_summary": True,
            "signals": True,
            "trade_approvals": "workflow_pending",
            "risk_status": True,
            "agent_theater": True,
            "push_registration": True,
            "push_delivery": "pending_fcm_credentials",
        },
        "latest_account": {
            "login_masked": latest_account.login_masked,
            "server": latest_account.server,
            "currency": latest_account.currency,
            "equity": latest_account.equity,
            "positions_count": latest_account.positions_count,
            "risk_mode": latest_account.risk_mode,
        }
        if latest_account
        else None,
        "accounts_count": accounts_count,
    }


def _registration_id() -> str:
    return f"push_{secrets.token_hex(8)}"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/push/register", response_model=MobilePushRegistrationOut)
def register_push(
    payload: MobilePushRegisterRequest,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> MobilePushRegistration:
    token_hash = _token_hash(payload.push_token)
    existing = db.scalar(
        select(MobilePushRegistration).where(
            MobilePushRegistration.user_id == principal.user_id,
            MobilePushRegistration.device_id == payload.device_id,
            MobilePushRegistration.provider == payload.provider,
        )
    )
    if existing:
        existing.token_hash = token_hash
        existing.platform = payload.platform
        existing.language = payload.language
        existing.preferences_json = payload.preferences_json
        existing.enabled = True
        existing.updated_at = utcnow()
        registration = existing
    else:
        registration = MobilePushRegistration(
            registration_id=_registration_id(),
            user_id=principal.user_id,
            provider=payload.provider,
            device_id=payload.device_id,
            token_hash=token_hash,
            platform=payload.platform,
            language=payload.language,
            preferences_json=payload.preferences_json,
        )
        db.add(registration)
    audit(db, principal, "register", "mobile_push", payload.device_id, {"provider": payload.provider, "platform": payload.platform})
    db.commit()
    db.refresh(registration)
    return registration


@router.get("/push/registrations", response_model=list[MobilePushRegistrationOut])
def list_push_registrations(
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> list[MobilePushRegistration]:
    return list(
        db.scalars(
            select(MobilePushRegistration)
            .where(MobilePushRegistration.user_id == principal.user_id)
            .order_by(MobilePushRegistration.updated_at.desc())
            .limit(50)
        )
    )


@router.get("/summary")
def mobile_summary(
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict:
    permissions = list(
        db.scalars(select(PermissionAssignment).where(PermissionAssignment.user_id == principal.user_id, PermissionAssignment.enabled.is_(True)).limit(100))
    )
    notifications = list(
        db.scalars(select(NotificationEvent).where(NotificationEvent.user_id == principal.user_id).order_by(NotificationEvent.created_at.desc()).limit(20))
    )
    approvals = list(
        db.scalars(
            select(TradeApproval)
            .where(TradeApproval.user_id == principal.user_id, TradeApproval.status == "pending")
            .order_by(TradeApproval.created_at.desc())
            .limit(20)
        )
    )
    return {
        "user_id": principal.user_id,
        "role": principal.role,
        "environment": "demo",
        "trading_mode": "monitor_only",
        "permissions": [permission.permission for permission in permissions],
        "recent_notifications": [
            {
                "event_id": notification.event_id,
                "level": notification.level,
                "title": notification.title,
                "status": notification.status,
                "created_at": iso_local(notification.created_at),
            }
            for notification in notifications
        ],
        "pending_approvals": [
            {
                "approval_id": approval.approval_id,
                "account_id": approval.account_id,
                "strategy_id": approval.strategy_id,
                "symbol": approval.symbol,
                "side": approval.side,
                "volume": approval.volume,
                "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
            }
            for approval in approvals
        ],
        "approval_flow": "manual_approval_api_ready",
        "execution": "blocked_without_execution_guard",
    }

