from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class AgentCatalogEntry:
    name: str
    role: str
    status: str
    tool_policy: str
    notes: str


AGENT_CATALOG: tuple[AgentCatalogEntry, ...] = (
    AgentCatalogEntry("Orchestrator Agent", "Coordinates monitored workflows and routes safe tasks.", "operational", "governed", "Health loop and task routing are live."),
    AgentCatalogEntry("Market Data Agent", "Reads MT5 bridge market telemetry.", "operational", "read_only", "Ticks/candles are monitor-only and quality gated."),
    AgentCatalogEntry("Technical Analysis Agent", "Summarizes candle-derived technical state.", "operational", "read_only", "No executable BUY/SELL signals until governance gates pass."),
    AgentCatalogEntry("Fundamental Analysis Agent", "Tracks fundamental-analysis readiness.", "operational_monitor", "read_only", "External fundamental provider is not connected yet."),
    AgentCatalogEntry("News Impact Agent", "Tracks economic-calendar/news halt readiness.", "operational_monitor", "read_only", "News feed adapter remains conservative until configured."),
    AgentCatalogEntry("Strategy Agent", "Tracks strategy registry and proposal tasks.", "operational_monitor", "governed", "Strategy proposals remain non-executable."),
    AgentCatalogEntry("Risk Manager", "Monitors account risk and approval gates.", "operational", "governed", "Auto execution remains disabled."),
    AgentCatalogEntry("Signal Reviewer", "Reviews safe signal proposal tasks.", "operational", "governed", "No live setup is under review by default."),
    AgentCatalogEntry("Execution Agent", "Observes execution readiness.", "operational", "no_direct_mt5", "Cannot send directly to MT5."),
    AgentCatalogEntry("Journal Agent", "Tracks journaling readiness.", "operational_monitor", "read_write_journal", "Trade journal storage is scaffolded."),
    AgentCatalogEntry("Backtest Agent", "Tracks backtest task readiness.", "operational_monitor", "sandbox_only", "Backtest engine integration is later roadmap."),
    AgentCatalogEntry("Forward Test Agent", "Tracks forward-test readiness.", "operational_monitor", "sandbox_only", "Forward-test scheduler integration is later roadmap."),
    AgentCatalogEntry("Strategy Tuning Agent", "Tracks tuning readiness.", "operational_monitor", "sandbox_only", "Parameter tuning remains approval-gated."),
    AgentCatalogEntry("Strategy Promotion Agent", "Tracks promotion lifecycle gates.", "operational_monitor", "governed", "Promotion requires validation records."),
    AgentCatalogEntry("Watchdog Agent", "Tracks service/watchdog readiness.", "operational_monitor", "read_only", "System health integration is active via orchestrator."),
    AgentCatalogEntry("Account Manager Agent", "Tracks account-management tasks.", "operational_monitor", "governed", "Account mutations require RBAC."),
    AgentCatalogEntry("Account Router Agent", "Tracks account-routing readiness.", "operational_monitor", "governed", "Execution routing remains disabled."),
    AgentCatalogEntry("Notification Agent", "Tracks notification adapter readiness.", "operational_monitor", "adapter_pending", "Telegram/WhatsApp/email credentials not configured."),
    AgentCatalogEntry("Localization Agent", "Tracks bilingual workflow readiness.", "operational_monitor", "read_only", "Locale foundations exist."),
    AgentCatalogEntry("Security Review Agent", "Tracks security review tasks.", "operational_monitor", "read_only", "Security review remains required before live trading."),
    AgentCatalogEntry("Deployment Agent", "Tracks deployment/rollback tasks.", "operational_monitor", "governed", "Deployments require backup/changelog/rollback records."),
    AgentCatalogEntry("System Improvement Agent", "Tracks improvement tasks.", "operational_monitor", "governed", "Improvement tasks are queued through the workflow engine."),
    AgentCatalogEntry("System Evolution Agent", "Tracks system evolution tasks.", "operational_monitor", "governed", "Production mutation requires approval."),
    AgentCatalogEntry("Broker Compatibility Agent", "Tracks broker compatibility readiness.", "operational_monitor", "read_only", "Broker checks are later roadmap."),
    AgentCatalogEntry("Market Data Quality Agent", "Tracks feed-quality readiness.", "operational_monitor", "read_only", "Telemetry freshness is live."),
    AgentCatalogEntry("Post-Trade Review Agent", "Tracks post-trade review readiness.", "operational_monitor", "read_only", "No closed trade workflow active yet."),
    AgentCatalogEntry("OpenClaw Gateway Agent", "Tracks optional OpenClaw gateway.", "disabled_by_default", "restricted", "OpenClaw remains human-facing only."),
    AgentCatalogEntry("Agent Theater Event Formatter", "Formats safe human-readable events.", "operational", "redacted_output_only", "Hidden reasoning and secrets are not exposed."),
)


def catalog_as_dicts() -> list[dict]:
    return [asdict(item) for item in AGENT_CATALOG]

