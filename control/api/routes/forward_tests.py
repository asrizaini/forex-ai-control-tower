from __future__ import annotations

import secrets
from datetime import datetime
from ..time_utils import utcnow

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import StrategyLabJobCreate, StrategyLabJobOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import StrategyLabJob

router = APIRouter(prefix="/forward-tests", tags=["forward-tests"])


@router.get("")
def list_resource() -> dict:
    return {"module": "forward_tests", "description": "Forward test jobs and results", "mode": "production-required"}


@router.get("/jobs", response_model=list[StrategyLabJobOut])
def list_forward_test_jobs(db: Session = Depends(get_db)) -> list[StrategyLabJob]:
    return list(db.scalars(select(StrategyLabJob).where(StrategyLabJob.job_type == "forward_test").order_by(StrategyLabJob.created_at.desc()).limit(200)))


@router.post("/jobs", response_model=StrategyLabJobOut)
def create_forward_test_job(
    payload: StrategyLabJobCreate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> StrategyLabJob:
    job = StrategyLabJob(
        job_id=f"ft_{secrets.token_hex(8)}",
        job_type="forward_test",
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        status="scheduled",
        parameters_json=payload.parameters_json,
        result_json={"note": "Forward-test scheduled; live signal/execution remains disabled until governance gates pass."},
        created_by=principal.user_id,
        updated_at=utcnow(),
    )
    db.add(job)
    audit(db, principal, "schedule", "forward_test_job", job.job_id, {"strategy_id": payload.strategy_id})
    db.commit()
    db.refresh(job)
    return job

