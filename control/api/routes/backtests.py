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
from strategies.lab import SCHEDULES, deterministic_backtest_result

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("")
def list_resource() -> dict:
    return {"module": "backtests", "description": "Backtest jobs and results", "mode": "production-required"}


@router.get("/schedules")
def schedules() -> dict:
    return {"schedules": SCHEDULES}


@router.get("/jobs", response_model=list[StrategyLabJobOut])
def list_backtest_jobs(db: Session = Depends(get_db)) -> list[StrategyLabJob]:
    return list(db.scalars(select(StrategyLabJob).where(StrategyLabJob.job_type == "backtest").order_by(StrategyLabJob.created_at.desc()).limit(200)))


@router.post("/jobs", response_model=StrategyLabJobOut)
def create_backtest_job(
    payload: StrategyLabJobCreate,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> StrategyLabJob:
    result = deterministic_backtest_result(payload.strategy_id, payload.symbol, payload.timeframe)
    job = StrategyLabJob(
        job_id=f"bt_{secrets.token_hex(8)}",
        job_type="backtest",
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        status="completed_mock",
        parameters_json=payload.parameters_json,
        result_json=result,
        quality_score=result["quality_score"],
        created_by=principal.user_id,
        updated_at=utcnow(),
    )
    db.add(job)
    audit(db, principal, "create", "backtest_job", job.job_id, {"strategy_id": payload.strategy_id, "mock_safe": True})
    db.commit()
    db.refresh(job)
    return job


@router.get("/leaderboard", response_model=list[StrategyLabJobOut])
def leaderboard(db: Session = Depends(get_db)) -> list[StrategyLabJob]:
    return list(
        db.scalars(
            select(StrategyLabJob)
            .where(StrategyLabJob.job_type == "backtest", StrategyLabJob.quality_score.is_not(None))
            .order_by(StrategyLabJob.quality_score.desc())
            .limit(50)
        )
    )

