from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from ..dependencies import current_principal
from ..auth import Principal
from ..permissions import has_permission

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("")
def list_resource() -> dict:
    return {"module": "risk", "description": "Risk status and kill-switch controls", "mode": "production-required"}


@router.post("/kill-switch")
def kill_switch(payload: dict, principal: Principal = Depends(current_principal)) -> dict:
    if not has_permission(principal.role, "system:halt"):
        raise HTTPException(status_code=403, detail="Permission denied")
    return {"halt_scope": payload.get("scope", "all_execution"), "active": True, "overrides_agents": True}

