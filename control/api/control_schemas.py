from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=80)
    email: EmailStr
    role: str = "viewer"
    language: str = "en"


class UserOut(UserCreate):
    id: int
    enabled: bool
    onboarding_complete: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountCreate(BaseModel):
    account_id: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=160)
    environment: str = "demo"
    account_group: str = "default"
    trading_mode: str = "monitor_only"


class AccountOut(AccountCreate):
    id: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyCreate(BaseModel):
    strategy_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=160)
    version: str = "0.1.0"
    owner: str = "system"
    lifecycle_state: str = "draft"
    allowed_environments: list[str] = Field(default_factory=lambda: ["dev", "staging", "demo"])
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class StrategyOut(StrategyCreate):
    id: int
    live_approval_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyPromoteRequest(BaseModel):
    target_state: str = Field(max_length=60)
    notes: str = Field(default="", max_length=500)
    rollback_target: str | None = Field(default=None, max_length=100)
    approve_production_live: bool = False


class StrategyApprovalOut(BaseModel):
    id: int
    strategy_id: str
    target_state: str
    status: str
    approver: str
    gate: str
    notes: str
    rollback_target: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyLabJobCreate(BaseModel):
    strategy_id: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=40)
    timeframe: str = Field(min_length=1, max_length=20)
    parameters_json: dict[str, Any] = Field(default_factory=dict)


class StrategyLabJobOut(BaseModel):
    id: int
    job_id: str
    job_type: str
    strategy_id: str
    symbol: str
    timeframe: str
    status: str
    parameters_json: dict[str, Any]
    result_json: dict[str, Any]
    quality_score: float | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    level: str = Field(default="normal", max_length=40)
    notification_type: str = Field(default="system_alert", max_length=80)
    user_id: str | None = Field(default=None, max_length=80)
    account_id: str | None = Field(default=None, max_length=80)
    title: str = Field(max_length=200)
    message: str = Field(default="", max_length=1000)
    language: str = "en"
    quiet_hours_enabled: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NotificationOut(BaseModel):
    id: int
    event_id: str
    level: str
    notification_type: str
    user_id: str | None
    account_id: str | None
    title: str
    message: str
    language: str
    routed_channels: list
    pending_channels: list
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class LlmRouteRequest(BaseModel):
    task_type: str = Field(default="general", max_length=120)
    prompt: str = Field(max_length=4000)
    paid_requested: bool = False
    estimated_cost: float = 0.0
    model: str = ""
    strategy_id: str | None = None


class LlmRouteOut(BaseModel):
    request_id: str
    provider: str
    paid_allowed: bool
    reason: str
    prompt_redacted: bool
    approved: bool


class LlmUsageOut(BaseModel):
    id: int
    request_id: str
    provider: str
    model: str
    task_type: str
    user_id: str | None
    strategy_id: str | None
    units: int
    estimated_cost: float
    approved: bool
    fallback_reason: str
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelEvaluationCreate(BaseModel):
    provider: str = Field(max_length=40)
    model: str = Field(max_length=120)
    task_type: str = Field(max_length=120)
    score: float = Field(ge=0, le=100)
    latency_ms: int = 0
    estimated_cost: float = 0.0
    feedback_json: dict[str, Any] = Field(default_factory=dict)


class ModelEvaluationOut(ModelEvaluationCreate):
    id: int
    evaluation_id: str
    accepted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    user_id: str
    permission: str
    account_id: str | None = None
    strategy_id: str | None = None


class PermissionOut(PermissionCreate):
    id: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskPolicyCreate(BaseModel):
    scope: str = "global"
    account_id: str | None = None
    strategy_id: str | None = None
    max_daily_loss_pct: float = 0.0
    max_weekly_loss_pct: float = 0.0
    max_open_trades: int = 0
    max_trades_per_day: int = 0
    max_spread_points: float = 0.0
    auto_execution_enabled: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RiskPolicyOut(RiskPolicyCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecutionGuardCheckRequest(BaseModel):
    account_id: str = Field(min_length=1, max_length=80)
    strategy_id: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=40)
    side: str = Field(pattern="^(BUY|SELL)$")
    volume: float = Field(gt=0)
    environment: str = "demo"
    trading_mode: str = "monitor_only"
    live_order: bool = False
    manual_approval: bool = False
    order_check_passed: bool = False
    system_health_score: int = Field(default=100, ge=0, le=100)
    kill_switch_active: bool = False
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    open_trades: int = 0
    trades_today: int = 0
    spread_points: float | None = None
    slippage_points: float | None = None
    market_data_quality_ok: bool = False
    broker_compatibility_ok: bool = False
    margin_available: bool = False
    duplicate_trade_risk: bool = True
    correlation_exposure_ok: bool = False
    news_halt_active: bool = True


class ExecutionGuardCheckOut(BaseModel):
    approved: bool
    reasons: list[str]
    token_issued: bool
    checks: dict[str, bool]
    effective_environment: str
    effective_trading_mode: str
    policy_id: int | None


class KillSwitchCreate(BaseModel):
    scope: str = Field(max_length=60)
    target_id: str | None = Field(default=None, max_length=160)
    reason: str = Field(default="", max_length=500)


class KillSwitchOut(KillSwitchCreate):
    id: int
    active: bool
    created_by: str
    deactivated_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: int
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any]
    created_at: datetime
    note: str

    model_config = {"from_attributes": True}


class WorkerTelemetryIn(BaseModel):
    worker: str = Field(min_length=1, max_length=80)
    result: dict[str, Any] = Field(default_factory=dict)


class MarketSnapshotOut(BaseModel):
    id: int
    worker: str
    symbol: str
    trend: str
    spread: float | None
    freshness_seconds: int | None
    rates_count: int
    feed_fresh: bool
    data_quality: str
    payload_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoricalCandleOut(BaseModel):
    id: int
    source: str
    symbol: str
    timeframe: str
    candle_time: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    tick_volume: float | None
    spread: float | None
    payload_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountSnapshotOut(BaseModel):
    id: int
    worker: str
    login_masked: str
    server: str
    currency: str
    balance: float | None
    equity: float | None
    margin_free: float | None
    drawdown_pct: float | None
    positions_count: int
    trade_allowed: bool | None
    risk_mode: str
    auto_execution_enabled: bool
    payload_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=256)
    totp_code: str | None = Field(default=None, max_length=12)


class BootstrapAdminRequest(BaseModel):
    user_id: str = Field(default="admin", max_length=80)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class SetPasswordRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=256)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class ServiceApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    permissions: list[str] = Field(default_factory=list)


class ServiceApiKeyOut(BaseModel):
    id: int
    key_id: str
    name: str
    permissions: list[str]
    enabled: bool
    created_by: str
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceApiKeyCreated(ServiceApiKeyOut):
    api_key: str


class AgentTaskCreate(BaseModel):
    assigned_agent: str = Field(min_length=1, max_length=120)
    task_type: str = Field(min_length=1, max_length=120)
    priority: int = Field(default=5, ge=1, le=10)
    request_json: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)


class AgentTaskUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=60)
    result_json: dict[str, Any] = Field(default_factory=dict)


class AgentTaskOut(BaseModel):
    id: int
    task_id: str
    requested_by: str
    assigned_agent: str
    task_type: str
    status: str
    priority: int
    request_json: dict[str, Any]
    result_json: dict[str, Any]
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentMessageCreate(BaseModel):
    task_id: str | None = None
    sender_agent: str = Field(min_length=1, max_length=120)
    recipient_agent: str = Field(min_length=1, max_length=120)
    message_type: str = Field(default="status", max_length=80)
    payload_json: dict[str, Any] = Field(default_factory=dict)


class AgentMessageOut(BaseModel):
    id: int
    message_id: str
    task_id: str | None
    sender_agent: str
    recipient_agent: str
    message_type: str
    payload_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentStateUpdate(BaseModel):
    status: str = Field(default="standby", max_length=60)
    state_json: dict[str, Any] = Field(default_factory=dict)


class AgentStateOut(BaseModel):
    id: int
    agent_name: str
    status: str
    heartbeat_at: datetime | None
    state_json: dict[str, Any]
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentToolPolicyCreate(BaseModel):
    agent_name: str = Field(min_length=1, max_length=120)
    tool_name: str = Field(min_length=1, max_length=120)
    allowed: bool = False
    environment: str = "demo"
    reason: str = ""


class AgentToolPolicyOut(AgentToolPolicyCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReleaseRecordCreate(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    environment: str = Field(default="staging", pattern="^(dev|staging|demo|production-live)$")
    changelog: str = Field(min_length=1, max_length=4000)
    backup_point: str = Field(min_length=1, max_length=255)
    test_result: str = Field(min_length=1, max_length=120)
    approver: str = Field(min_length=1, max_length=120)
    rollback_command: str = Field(min_length=1, max_length=1000)
    rollback_target: str | None = Field(default=None, max_length=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ReleaseRecordOut(ReleaseRecordCreate):
    id: int
    deployment_id: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReleaseStatusUpdate(BaseModel):
    status: str = Field(pattern="^(planned|approved|deployed|failed|rolled_back)$")
    test_result: str | None = Field(default=None, max_length=120)
    notes: str = Field(default="", max_length=500)


class MobilePushRegisterRequest(BaseModel):
    provider: str = Field(default="fcm", pattern="^(fcm|apns|browser)$")
    platform: str = Field(default="android", pattern="^(android|ios|web)$")
    device_id: str = Field(min_length=1, max_length=160)
    push_token: str = Field(min_length=16, max_length=4096)
    language: str = Field(default="en", pattern="^(en|ms-MY|auto)$")
    preferences_json: dict[str, Any] = Field(default_factory=dict)


class MobilePushRegistrationOut(BaseModel):
    id: int
    registration_id: str
    user_id: str
    provider: str
    device_id: str
    platform: str
    language: str
    enabled: bool
    preferences_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TradeApprovalCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=80)
    account_id: str = Field(min_length=1, max_length=80)
    strategy_id: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=40)
    side: str = Field(pattern="^(BUY|SELL)$")
    volume: float = Field(gt=0)
    environment: str = Field(default="demo", pattern="^(dev|staging|demo|production-live)$")
    trading_mode: str = Field(default="manual_live", max_length=40)
    reason: str = Field(default="", max_length=1000)
    guard_check_json: dict[str, Any] = Field(default_factory=dict)
    expires_minutes: int = Field(default=10, ge=1, le=120)


class TradeApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str = Field(default="", max_length=1000)


class TradeApprovalOut(BaseModel):
    id: int
    approval_id: str
    user_id: str
    account_id: str
    strategy_id: str
    symbol: str
    side: str
    volume: float
    environment: str
    trading_mode: str
    status: str
    requested_by: str
    decided_by: str | None
    reason: str
    guard_check_json: dict[str, Any]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
