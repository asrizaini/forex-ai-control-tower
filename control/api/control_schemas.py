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
