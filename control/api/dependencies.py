from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from .auth import Principal, decode_token


def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    principal = decode_token(token)
    if not principal:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return principal
