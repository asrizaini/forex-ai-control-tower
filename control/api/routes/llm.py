from __future__ import annotations

import secrets
from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import LlmRouteOut, LlmRouteRequest, LlmUsageOut, ModelEvaluationCreate, ModelEvaluationOut
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import LlmUsage, ModelEvaluation
from llm_cost_center.router import choose_provider, redact_prompt
from model_evaluation.evaluator import evaluate_model_result

router = APIRouter(prefix="/llm", tags=["llm"])

DAILY_LIMIT = 5.0
MONTHLY_LIMIT = 100.0
APPROVAL_THRESHOLD = 1.0


def _daily_spend(db: Session) -> float:
    start = datetime.combine(date.today(), time.min)
    return float(db.scalar(select(func.coalesce(func.sum(LlmUsage.estimated_cost), 0.0)).where(LlmUsage.created_at >= start)) or 0.0)


@router.get("/budget")
def budget(db: Session = Depends(get_db)) -> dict:
    spend = _daily_spend(db)
    return {"daily_limit": DAILY_LIMIT, "monthly_limit": MONTHLY_LIMIT, "daily_spend": spend, "approval_threshold": APPROVAL_THRESHOLD}


@router.post("/route", response_model=LlmRouteOut)
def route_llm(payload: LlmRouteRequest, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> LlmRouteOut:
    redacted = redact_prompt(payload.prompt)
    route = choose_provider(payload.task_type, payload.estimated_cost, _daily_spend(db), DAILY_LIMIT, payload.paid_requested)
    approved = route["provider"] == "local" or (route["paid_allowed"] and payload.estimated_cost <= APPROVAL_THRESHOLD)
    request_id = f"llm_{secrets.token_hex(8)}"
    usage = LlmUsage(
        request_id=request_id,
        provider=route["provider"],
        model=payload.model,
        task_type=payload.task_type,
        user_id=principal.user_id,
        strategy_id=payload.strategy_id,
        units=len(redacted.split()),
        estimated_cost=payload.estimated_cost if route["provider"] != "local" else 0.0,
        approved=approved,
        fallback_reason=route["reason"],
        metadata_json={"prompt_redacted": redacted != payload.prompt, "mock_safe": True},
    )
    db.add(usage)
    audit(db, principal, "route", "llm_request", request_id, {"provider": route["provider"], "approved": approved, "reason": route["reason"]})
    db.commit()
    return LlmRouteOut(
        request_id=request_id,
        provider=route["provider"],
        paid_allowed=route["paid_allowed"],
        reason=route["reason"],
        prompt_redacted=redacted != payload.prompt,
        approved=approved,
    )


@router.get("/usage", response_model=list[LlmUsageOut])
def usage(db: Session = Depends(get_db)) -> list[LlmUsage]:
    return list(db.scalars(select(LlmUsage).order_by(LlmUsage.created_at.desc()).limit(200)))


@router.post("/evaluations", response_model=ModelEvaluationOut)
def create_evaluation(payload: ModelEvaluationCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> ModelEvaluation:
    result = evaluate_model_result({"score": payload.score})
    evaluation = ModelEvaluation(
        evaluation_id=f"eval_{secrets.token_hex(8)}",
        provider=payload.provider,
        model=payload.model,
        task_type=payload.task_type,
        score=payload.score,
        latency_ms=payload.latency_ms,
        estimated_cost=payload.estimated_cost,
        accepted=bool(result["accepted"]),
        feedback_json=payload.feedback_json,
    )
    db.add(evaluation)
    audit(db, principal, "create", "model_evaluation", evaluation.evaluation_id, {"score": payload.score, "accepted": evaluation.accepted})
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.get("/evaluations", response_model=list[ModelEvaluationOut])
def evaluations(db: Session = Depends(get_db)) -> list[ModelEvaluation]:
    return list(db.scalars(select(ModelEvaluation).order_by(ModelEvaluation.created_at.desc()).limit(200)))
