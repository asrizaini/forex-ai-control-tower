from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import StrategyLabJobCreate, StrategyLabJobOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import StrategyLabJob

router = APIRouter(prefix="/tuning", tags=["tuning"])


@router.get("")
def list_resource() -> dict:
    return {"module": "tuning", "description": "Strategy tuning jobs", "mode": "production-required"}


@router.get("/jobs", response_model=list[StrategyLabJobOut])
def list_tuning_jobs(db: Session = Depends(get_db)) -> list[StrategyLabJob]:
    return list(db.scalars(select(StrategyLabJob).where(StrategyLabJob.job_type == "tuning").order_by(StrategyLabJob.created_at.desc()).limit(200)))


@router.post("/jobs", response_model=StrategyLabJobOut)
def create_tuning_job(
    payload: StrategyLabJobCreate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> StrategyLabJob:
    job = StrategyLabJob(
        job_id=f"tun_{secrets.token_hex(8)}",
        job_type="tuning",
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        status="queued",
        parameters_json=payload.parameters_json,
        result_json={"overfitting_detection": "required_before_promotion", "mock_safe": True},
        created_by=principal.user_id,
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    audit(db, principal, "queue", "tuning_job", job.job_id, {"strategy_id": payload.strategy_id})
    db.commit()
    db.refresh(job)
    return job

