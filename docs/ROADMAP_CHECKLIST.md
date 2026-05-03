# Forex AI Control Tower Roadmap Checklist

Status legend:

- `[x]` Implemented and deployed
- `[~]` Scaffolded or partially implemented
- `[ ]` Not implemented yet
- `[!]` Blocked by credentials, policy, broker/API access, or production validation

This checklist tracks the original full-system prompt. The current deployment is a secure scaffold plus working infrastructure, not a completed autonomous trading platform.

## Current Production Runtime

- `[x]` GitHub repository created and pushed.
- `[x]` Fixed IP inventory for six machines.
- `[x]` Dockerized Ansible controller runner.
- `[x]` Linux bootstrap on machines 1-5.
- `[x]` Docker enabled on Linux nodes.
- `[x]` Control stack running on `10.10.1.81`.
- `[x]` PostgreSQL, Redis, Qdrant, Prometheus, Grafana, Loki running.
- `[x]` Grafana admin password reset and recovery email set.
- `[x]` Grafana Prometheus and Loki datasources provisioned.
- `[x]` Grafana overview dashboard provisioned.
- `[x]` Blackbox exporter reachability monitoring.
- `[x]` Control API running on `10.10.1.81:8000`.
- `[x]` Dashboard running on `10.10.1.81:5173`.
- `[x]` Ollama installed on LLM nodes.
- `[x]` Market worker service enabled on machine 4.
- `[x]` Strategy/risk worker service enabled on machine 5.
- `[x]` Windows MT5 bridge installed on machine 6.
- `[x]` MT5 bridge connected to installed demo MT5 terminal.
- `[x]` Runtime secrets rotated without printing values.
- `[x]` Services enabled for restart after reboot where safe.
- `[x]` Linux node exporters deployed on machines 1-5.
- `[x]` Windows exporter deployed on machine 6.
- `[x]` Orchestrator runtime service enabled on control node.
- `[x]` Agent Theater live safe event feed enabled.
- `[x]` Market and strategy/risk workers publish safe Agent Theater events.
- `[x]` Market worker reads MT5 bridge symbols, ticks, and M1 candle snapshots in monitor-only mode.
- `[x]` Strategy/risk worker reads MT5 bridge account and open-position state in monitor-only mode.
- `[x]` Agent Theater reports stale/limited MT5 market data as blocked for signal commentary.
- `[x]` Agent Theater WebSocket live chat stream enabled.
- `[x]` Agent Theater events pushed to Loki and visible in Grafana.
- `[x]` Human-style Agent Theater dialogue templates for market, technical, news, strategy, risk, signal review, notification, and execution status.
- `[x]` Grafana-embedded Orchestrator Console for operator chat and safe agent task routing.
- `[x]` Local Ollama-backed general Orchestrator chat enabled with safety fallback.
- `[x]` Postgres-backed control-plane tables initialized.
- `[x]` Worker telemetry snapshots persisted to PostgreSQL through the control API.
- `[x]` Dashboard displays latest MT5 account and market telemetry.
- `[x]` Initial admin user, demo account, monitor-only strategy, and global risk policy seeded.

## Safety Defaults

- `[x]` No hardcoded committed secrets.
- `[x]` `.env`, keys, tokens, logs, and generated secrets ignored.
- `[x]` Default trading mode is `monitor_only`.
- `[x]` Default execution environment is `demo`.
- `[x]` Live auto-trading disabled by default.
- `[x]` MT5 bridge default mode is demo.
- `[x]` `ALLOW_LIVE_TRADING=false` default.
- `[x]` `REQUIRE_ORDER_CHECK=true` default.
- `[x]` Order send requires prior order check.
- `[x]` Order send requires Execution Guard approval token.
- `[x]` Runtime secrets are environment-driven with no committed secret material.
- `[x]` Secret manager provider configuration added for env, Vault, SOPS, and cloud providers; active env provider is verifiable through API/dashboard, external provider activation is an operator choice before live trading.

## Core API And Dashboard

- `[x]` FastAPI application scaffold.
- `[x]` `/health`, `/metrics`, `/docs`, `/openapi.json`.
- `[x]` `/api/v1` route structure.
- `[x]` JWT signing/verification helper.
- `[x]` Deny-by-default permission helper tests.
- `[x]` Authenticated WebSocket skeletons.
- `[x]` Dashboard shows environment, health, risk, localization, orchestrator, and Agent Theater event panels.
- `[x]` Dashboard shows latest persisted MT5 account/market snapshots.
- `[x]` Real multi-user login UI.
- `[x]` User management database foundation.
- `[x]` Account management database foundation.
- `[x]` Persistent audit event browser.
- `[x]` Real RBAC policy storage and admin UI.
- `[x]` 2FA setup/enable flow.
- `[x]` Refresh token flow.
- `[x]` Service API key management.

## Main Orchestrator And Agents

- `[x]` Agent modules scaffolded.
- `[x]` Structured message concept scaffolded.
- `[x]` Safe Orchestrator runtime monitoring loop.
- `[x]` Market Data Agent operational monitor.
- `[x]` Technical Analysis Agent operational monitor.
- `[x]` Fundamental Analysis Agent operational monitor.
- `[x]` News Impact Agent operational monitor.
- `[x]` Strategy Agent operational monitor.
- `[x]` Risk Manager Agent operational monitor.
- `[x]` Signal Reviewer Agent operational monitor.
- `[x]` Execution Agent operational monitor.
- `[x]` Journal Agent operational monitor.
- `[x]` Backtest Agent operational monitor.
- `[x]` Forward Test Agent operational monitor.
- `[x]` Strategy Tuning Agent operational monitor.
- `[x]` Strategy Promotion Agent operational monitor.
- `[x]` Watchdog Agent operational monitor.
- `[x]` Account Manager and Router Agent operational monitors.
- `[x]` Notification, Localization, Security, Deployment, and Improvement Agent operational monitors.
- `[x]` Real database-backed message bus between agents.
- `[x]` Durable workflow engine for safe queued agent tasks.
- `[x]` Agent task queue and retry model.
- `[x]` Agent state persistence.
- `[x]` Agent permissions and tool policy enforcement.
- `[x]` Production orchestrator decision loop for health, task routing, and safe agent workflow orchestration; executable trading remains approval-gated under Execution Guard/Risk sections.

## Agent Theater / AI Trading Room

- `[x]` Agent Theater module scaffold.
- `[x]` Event schema, formatter, redaction, sample events.
- `[x]` WebSocket route for live event stream.
- `[x]` Dashboard live Agent Theater event feed.
- `[x]` Live event ingestion from agents; worker-side market, technical, strategy, and risk summaries are live.
- `[x]` Live chat stream over WebSocket.
- `[x]` Operator-to-Orchestrator chat UI embedded in Grafana.
- `[x]` Orchestrator chat publishes operator messages, agent task acknowledgements, and safe replies into the Theater transcript.
- `[x]` Human-readable trading-room style status messages.
- `[x]` Room catalog API for Live Chat View, Workflow Timeline, Debate Mode, Boardroom Mode, Strategy War Room, Account Routing Room, and System Improvement Room.
- `[x]` Debate Mode safe challenge summaries between Strategy Agent and Risk Manager.
- `[x]` System Improvement Room for roadmap, deployment, rollback, test, and audit coordination.
- `[x]` Bilingual rendered event stream labels and selected safe summaries for English and Bahasa Melayu Malaysia.
- `[~]` Real market/news/strategy content in dialogue; current messages honestly show standby or pending-adapter status until integrations are complete.
- `[~]` Workflow Timeline.
- `[~]` Boardroom Mode.
- `[~]` Strategy War Room.
- `[~]` Account Routing Room.

## Execution Guard And Risk

- `[x]` Execution Guard token primitive.
- `[x]` MT5 bridge rejects order send without guard token.
- `[x]` MT5 bridge rejects order send before order check.
- `[x]` Live trading disabled by default.
- `[~]` Risk engine scaffold.
- `[~]` Kill switch module scaffold.
- `[~]` Governance scaffold.
- `[x]` Account permission check.
- `[x]` User permission check.
- `[x]` Strategy permission check.
- `[x]` Trading mode policy enforcement in Execution Guard control-plane check.
- `[x]` Max daily and weekly loss checks.
- `[x]` Max open trades and trades per day checks.
- `[~]` Spread and slippage checks from broker telemetry payload; direct MT5 telemetry binding still pending.
- `[~]` News halt integration as an Execution Guard input; live news provider still pending.
- `[~]` Duplicate trade risk detection as an Execution Guard input; position/signal matching still pending.
- `[~]` Margin availability validation as an Execution Guard input; MT5 account binding still pending.
- `[~]` Correlation exposure checks as an Execution Guard input; portfolio exposure model still pending.
- `[ ]` Broker compatibility enforcement.
- `[ ]` Market data quality enforcement.
- `[ ]` System health score execution gating.
- `[ ]` Global and scoped kill switch API fully wired.

## MT5 Bridge

- `[x]` FastAPI bridge service.
- `[x]` `/health` and `/metrics`.
- `[x]` `/account`, `/symbols`, `/rates/{symbol}`, `/ticks/{symbol}`.
- `[x]` `/order/check`, `/order/send`, `/positions`, `/history`.
- `[x]` Demo MT5 terminal detected.
- `[x]` Bridge token protection.
- `[x]` Windows scheduled task startup.
- `[~]` Multi-account terminal manager scaffold.
- `[ ]` One MT5 terminal instance per account.
- `[ ]` Per-account bridge ports `8501+`.
- `[ ]` Account profile persistence.
- `[ ]` Broker credential onboarding without secret leakage.
- `[ ]` Windows service mode alternative.
- `[ ]` Production MT5 bridge observability beyond basic health.

## Strategy Registry And Governance

- `[~]` Strategy registry/plugin skeleton.
- `[~]` Lifecycle states documented/scaffolded.
- `[~]` Governance modules scaffolded.
- `[ ]` Real strategy plugin loader.
- `[ ]` Strategy database.
- `[ ]` Strategy approval workflow UI.
- `[ ]` User/account/environment strategy permissions.
- `[ ]` Backtest status gate.
- `[ ]` Forward test status gate.
- `[ ]` Demo validation gate.
- `[ ]` Live approval gate.
- `[ ]` Rollback target enforcement.

## Backtest, Forward Test, And Tuning

- `[~]` Backtest, forward-test, and tuning route skeletons.
- `[~]` Agent skeletons.
- `[ ]` Backtest engine.
- `[ ]` Historical data storage.
- `[ ]` Forward-test scheduler.
- `[ ]` Walk-forward validation.
- `[ ]` Parameter tuning engine.
- `[ ]` Overfitting detection.
- `[ ]` Strategy leaderboard.
- `[ ]` Daily/weekend scheduled jobs.
- `[ ]` Quality scoring implementation.

## Market Data And News

- `[~]` Market worker service wrapper.
- `[~]` Market data quality checker scaffold.
- `[~]` Broker compatibility checker scaffold.
- `[~]` Real candle/tick collector; MT5 bridge snapshots are wired, durable storage still pending.
- `[~]` Technical indicator engine; short-term trend from M1 candles is wired, full indicator suite still pending.
- `[ ]` Multi-timeframe analyzer.
- `[ ]` Price action detector.
- `[ ]` Spread/slippage monitor.
- `[ ]` News/fundamental feed integration.
- `[ ]` High-impact news halt logic.
- `[ ]` Stale feed detection wired to execution guard.

## Localization

- `[x]` Locale directories for English and Bahasa Melayu Malaysia.
- `[x]` Localization service scaffold.
- `[x]` Glossary file.
- `[x]` Tests for non-translation rules.
- `[~]` Dashboard language selector.
- `[ ]` Full dashboard translation coverage.
- `[ ]` Notification translation coverage.
- `[ ]` Agent Theater translation coverage.
- `[ ]` Trade approval message translation coverage.
- `[ ]` Automatic language detection in live user workflows.

## Notifications

- `[~]` Notification hub scaffold.
- `[~]` Escalation matrix documented.
- `[ ]` Telegram integration.
- `[ ]` WhatsApp Business Cloud API integration.
- `[ ]` Mobile push integration.
- `[ ]` Email SMTP integration.
- `[ ]` Browser push integration.
- `[ ]` Discord/SMS optional integrations.
- `[ ]` Quiet hours.
- `[ ]` Approval/rejection workflows through notification channels.

## Paid And Local LLM Routing

- `[x]` Ollama installed with local model pulls.
- `[~]` Paid LLM gateway scaffold/mock mode.
- `[~]` LLM Cost Center scaffold.
- `[~]` Model Evaluation Center scaffold.
- `[ ]` Production model router.
- `[ ]` OpenAI API integration.
- `[ ]` Gemini API integration.
- `[ ]` Cost budgets and approval thresholds enforced.
- `[ ]` Secret redaction before paid LLM calls.
- `[ ]` Fallback-to-local policy enforcement.
- `[ ]` Model quality reports.

## OpenClaw Optional Gateway

- `[~]` OpenClaw gateway scaffold.
- `[x]` Disabled by default.
- `[~]` Allowed actions file.
- `[ ]` Real OpenClaw bridge.
- `[ ]` Admin/user chat workflows.
- `[ ]` Approval-only API action layer.
- `[ ]` Safety policy tests.

## Observability

- `[x]` Prometheus running.
- `[x]` Grafana running.
- `[x]` Loki running.
- `[x]` Blackbox exporter running.
- `[x]` Grafana dashboard provisioned.
- `[x]` Grafana Agent Theater log dashboard provisioned.
- `[x]` Reachability monitoring for fixed IP plan.
- `[x]` Linux node exporter on Linux hosts.
- `[x]` Windows exporter on MT5 host.
- `[x]` Host metrics dashboard provisioned.
- `[~]` Structured JSON logs in selected services.
- `[ ]` Docker/container dashboards.
- `[ ]` API request dashboards.
- `[ ]` Worker queue dashboards.
- `[ ]` Agent event dashboards.
- `[ ]` Trade/risk dashboards.
- `[ ]` Loki log ingestion from all services.
- `[ ]` Alert rules and notification routing.

## Backup, Restore, Deployment, Rollback

- `[~]` Backup/restore scripts scaffolded.
- `[~]` Deployment/rollback scripts scaffolded.
- `[x]` Runtime secret rotation playbook.
- `[x]` GitHub source control and rollback base.
- `[ ]` Scheduled backups.
- `[ ]` Backup verification.
- `[ ]` Restore drill.
- `[ ]` Deployment approval workflow.
- `[ ]` Release IDs, changelogs, approvers, rollback commands persisted.

## Mobile And External API Readiness

- `[x]` Mobile API contract docs.
- `[x]` Kotlin client example.
- `[~]` Mobile bootstrap route skeleton.
- `[~]` Push registration route skeleton.
- `[ ]` Real Android/iOS app.
- `[ ]` FCM credentials and push sender.
- `[ ]` Mobile 2FA.
- `[ ]` Mobile approval/rejection live flow.

## Production Readiness Gates Before Live Trading

- `[ ]` Real user/account persistence.
- `[ ]` Full RBAC and audit persistence.
- `[ ]` Real risk policies per account.
- `[ ]` Real strategy validation pipeline.
- `[ ]` Demo trading validation reports.
- `[ ]` Manual approval workflow proven.
- `[ ]` Restricted live auto-trading reviewed and approved.
- `[ ]` Secret manager deployed.
- `[ ]` Backup/restore drill passed.
- `[ ]` Monitoring alerts connected to notification hub.
- `[ ]` Security review completed.
- `[ ]` Broker compatibility checks passed.
- `[ ]` Market data quality gates passed.
- `[ ]` Kill switch tested.
- `[ ]` Production-live environment explicitly approved.
