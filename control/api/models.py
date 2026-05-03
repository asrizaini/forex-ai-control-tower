from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(40), default="viewer")
    language: Mapped[str] = mapped_column(String(16), default="en")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    environment: Mapped[str] = mapped_column(String(40), default="demo")
    account_group: Mapped[str] = mapped_column(String(80), default="default")
    trading_mode: Mapped[str] = mapped_column(String(40), default="monitor_only")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[str] = mapped_column(String(40), default="0.1.0")
    owner: Mapped[str] = mapped_column(String(120), default="system")
    lifecycle_state: Mapped[str] = mapped_column(String(60), default="draft")
    allowed_environments: Mapped[list] = mapped_column(JSON, default=lambda: ["dev", "staging", "demo"])
    live_approval_status: Mapped[str] = mapped_column(String(60), default="not_approved")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StrategyApproval(Base):
    __tablename__ = "strategy_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(100), index=True)
    target_state: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(60), default="approved", index=True)
    approver: Mapped[str] = mapped_column(String(120), index=True)
    gate: Mapped[str] = mapped_column(String(120), index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    rollback_target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class StrategyLabJob(Base):
    __tablename__ = "strategy_lab_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    job_type: Mapped[str] = mapped_column(String(60), index=True)
    strategy_id: Mapped[str] = mapped_column(String(100), index=True)
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    timeframe: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(60), default="queued", index=True)
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="system", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    level: Mapped[str] = mapped_column(String(40), index=True)
    notification_type: Mapped[str] = mapped_column(String(80), index=True)
    user_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    account_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="en", index=True)
    routed_channels: Mapped[list] = mapped_column(JSON, default=list)
    pending_channels: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(60), default="queued", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class LlmUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(120), default="", index=True)
    task_type: Mapped[str] = mapped_column(String(120), index=True)
    user_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    units: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    fallback_reason: Mapped[str] = mapped_column(String(160), default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(120), index=True)
    task_type: Mapped[str] = mapped_column(String(120), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    feedback_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PermissionAssignment(Base):
    __tablename__ = "permission_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(80), index=True)
    account_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    permission: Mapped[str] = mapped_column(String(120), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RiskPolicy(Base):
    __tablename__ = "risk_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(40), default="global")
    account_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    max_daily_loss_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_weekly_loss_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_open_trades: Mapped[int] = mapped_column(Integer, default=0)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, default=0)
    max_spread_points: Mapped[float] = mapped_column(Float, default=0.0)
    auto_execution_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KillSwitch(Base):
    __tablename__ = "kill_switches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(60), index=True)
    target_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="system", index=True)
    deactivated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), default="system", index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(80), index=True)
    resource_id: Mapped[str] = mapped_column(String(160), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    note: Mapped[str] = mapped_column(Text, default="")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker: Mapped[str] = mapped_column(String(80), default="market", index=True)
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    trend: Mapped[str] = mapped_column(String(80), default="unknown")
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    freshness_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rates_count: Mapped[int] = mapped_column(Integer, default=0)
    feed_fresh: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    data_quality: Mapped[str] = mapped_column(String(40), default="limited", index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker: Mapped[str] = mapped_column(String(80), default="strategy_risk", index=True)
    login_masked: Mapped[str] = mapped_column(String(80), default="***", index=True)
    server: Mapped[str] = mapped_column(String(120), default="unknown")
    currency: Mapped[str] = mapped_column(String(16), default="unknown")
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_free: Mapped[float | None] = mapped_column(Float, nullable=True)
    drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    positions_count: Mapped[int] = mapped_column(Integer, default=0)
    trade_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_mode: Mapped[str] = mapped_column(String(40), default="monitor_only", index=True)
    auto_execution_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class UserCredential(Base):
    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    password_salt: Mapped[str] = mapped_column(String(80))
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(80), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ServiceApiKey(Base):
    __tablename__ = "service_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="system", index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    requested_by: Mapped[str] = mapped_column(String(120), default="system", index=True)
    assigned_agent: Mapped[str] = mapped_column(String(120), index=True)
    task_type: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(60), default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=5, index=True)
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sender_agent: Mapped[str] = mapped_column(String(120), index=True)
    recipient_agent: Mapped[str] = mapped_column(String(120), index=True)
    message_type: Mapped[str] = mapped_column(String(80), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AgentState(Base):
    __tablename__ = "agent_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(60), default="standby", index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AgentToolPolicy(Base):
    __tablename__ = "agent_tool_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(120), index=True)
    tool_name: Mapped[str] = mapped_column(String(120), index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    environment: Mapped[str] = mapped_column(String(40), default="demo", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
