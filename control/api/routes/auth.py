from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal, issue_token
from ..control_schemas import BootstrapAdminRequest, LoginRequest, RefreshTokenRequest, SetPasswordRequest, TotpVerifyRequest
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import RefreshToken, User, UserCredential
from ..time_utils import utcnow
from ..permissions import has_permission
from ..security import (
    generate_totp_secret,
    hash_token,
    otpauth_uri,
    password_hash,
    random_token_urlsafe,
    refresh_expiry,
    verify_password,
    verify_totp,
)
from ..credential_store import runtime_value

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("")
def list_resource() -> dict:
    return {"module": "auth", "description": "Authentication and token lifecycle", "mode": "production-required"}


def _refresh_payload(db: Session, user: User) -> dict:
    refresh_token = random_token_urlsafe(48)
    db.add(RefreshToken(user_id=user.user_id, token_hash=hash_token(refresh_token), expires_at=refresh_expiry()))
    access = issue_token(user_id=user.user_id, role=user.role, account_ids=())
    return {**access, "refresh_token": refresh_token}


@router.post("/bootstrap-admin")
def bootstrap_admin(payload: BootstrapAdminRequest, db: Session = Depends(get_db)) -> dict:
    expected_password = runtime_value("LOCAL_ADMIN_BOOTSTRAP_PASSWORD")
    if runtime_value("LOCAL_AUTH_BOOTSTRAP_ENABLED", "false").lower() != "true" or not expected_password:
        raise HTTPException(status_code=503, detail="Local auth bootstrap is disabled")
    if payload.password != expected_password:
        raise HTTPException(status_code=403, detail="Bootstrap password does not match environment")
    existing_credential = db.scalar(select(UserCredential).where(UserCredential.user_id == payload.user_id))
    if existing_credential:
        raise HTTPException(status_code=409, detail="Admin credential already exists")
    user = db.scalar(select(User).where(User.user_id == payload.user_id))
    if not user:
        user = User(user_id=payload.user_id, email=str(payload.email), role="super_admin", language="en", onboarding_complete=True)
        db.add(user)
    digest, salt = password_hash(payload.password)
    db.add(UserCredential(user_id=payload.user_id, password_hash=digest, password_salt=salt))
    audit(db, None, "bootstrap_admin", "user", payload.user_id, {"role": "super_admin"})
    db.commit()
    return {"bootstrapped": True, "user_id": payload.user_id}


@router.post("/password")
def set_password(payload: SetPasswordRequest, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    if principal.user_id != payload.user_id and not has_permission(principal.role, "users:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    user = db.scalar(select(User).where(User.user_id == payload.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    digest, salt = password_hash(payload.password)
    credential = db.scalar(select(UserCredential).where(UserCredential.user_id == payload.user_id))
    if credential:
        credential.password_hash = digest
        credential.password_salt = salt
    else:
        db.add(UserCredential(user_id=payload.user_id, password_hash=digest, password_salt=salt))
    audit(db, principal, "set_password", "user", payload.user_id, {})
    db.commit()
    return {"updated": True}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.user_id == payload.user_id))
    credential = db.scalar(select(UserCredential).where(UserCredential.user_id == payload.user_id))
    if not user or not user.enabled or not credential:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, credential.password_hash, credential.password_salt):
        credential.failed_login_count += 1
        audit(db, None, "failed_login", "user", payload.user_id, {})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if credential.two_factor_enabled and not verify_totp(credential.totp_secret_encrypted, payload.totp_code):
        raise HTTPException(status_code=401, detail="2FA code required")
    credential.failed_login_count = 0
    credential.last_login_at = utcnow()
    audit(db, None, "login", "user", payload.user_id, {"role": user.role})
    token_payload = _refresh_payload(db, user)
    db.commit()
    return token_payload


@router.post("/refresh")
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> dict:
    token_hash = hash_token(payload.refresh_token)
    refresh_token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not refresh_token or refresh_token.revoked or refresh_token.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.scalar(select(User).where(User.user_id == refresh_token.user_id))
    if not user or not user.enabled:
        raise HTTPException(status_code=401, detail="User disabled")
    refresh_token.revoked = True
    token_payload = _refresh_payload(db, user)
    audit(db, None, "refresh_token", "user", user.user_id, {})
    db.commit()
    return token_payload


@router.get("/me")
def me(principal: Principal = Depends(current_principal)) -> dict:
    return {"user_id": principal.user_id, "role": principal.role, "account_ids": list(principal.account_ids)}


@router.post("/2fa/setup")
def setup_2fa(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    credential = db.scalar(select(UserCredential).where(UserCredential.user_id == principal.user_id))
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    secret = generate_totp_secret()
    credential.totp_secret_encrypted = secret
    credential.two_factor_enabled = False
    audit(db, principal, "setup_2fa", "user", principal.user_id, {})
    db.commit()
    return {"secret": secret, "otpauth_uri": otpauth_uri(principal.user_id, secret)}


@router.post("/2fa/enable")
def enable_2fa(payload: TotpVerifyRequest, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    credential = db.scalar(select(UserCredential).where(UserCredential.user_id == principal.user_id))
    if not credential or not verify_totp(credential.totp_secret_encrypted, payload.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    credential.two_factor_enabled = True
    audit(db, principal, "enable_2fa", "user", principal.user_id, {})
    db.commit()
    return {"enabled": True}

