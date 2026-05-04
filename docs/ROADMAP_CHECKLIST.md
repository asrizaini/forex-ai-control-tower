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
- `[x]` Laravel operator dashboard running on `10.10.1.81:8090` as an operations console over the FastAPI control plane.
- `[x]` Ollama installed on LLM nodes.
- `[x]` Market worker service enabled on machine 4.
- `[x]` Strategy/risk worker service enabled on machine 5.
- `[x]` Windows MT5 bridge installed on machine 6.
- `[x]` MT5 bridge connected to installed demo MT5 terminal.
- `[x]` Runtime secrets rotated without printing values.
- `[x]` Services enabled for restart after reboot where safe.
- `[x]` Firewall hardening applied across Linux nodes and Windows MT5 bridge with tower-subnet allow-listing.
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
- `[x]` Guarded live trading enable/disable playbooks added; enablement refuses to run unless all production-readiness gates are green and the exact operator confirmation phrase is supplied from environment.
- `[x]` Formal pre-live security review and explicit production-live approval audit records created through the control API.
- `[x]` Live runtime flags enabled on the control API and MT5 bridge after readiness gates passed.
- `[x]` Negative execution tests confirmed that direct order sends remain blocked without order_check and Execution Guard approval token.

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
- `[x]` Laravel operator dashboard scaffold deployed for readiness, account/market status, and pre-live gate visibility.
- `[!]` Laravel write-side approval forms; dashboard is intentionally read-first until authenticated audited POST workflows are expanded through FastAPI.

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
- `[!]` Real market/news/strategy content in dialogue; live market/account telemetry and news adapter decisions are present, but external provider configuration, full strategy scoring, and live strategy governance adapters are held in `docs/PENDING_HOLD_CHECKLIST.md`.
- `[x]` Workflow Timeline room with multi-agent safe transcript seed and live event filtering.
- `[x]` Boardroom Mode with executive status, risk posture, and security review summaries.
- `[x]` Strategy War Room with strategy, backtest, and promotion gate summaries.
- `[x]` Account Routing Room with account router, risk manager, and execution guard summaries.

## Execution Guard And Risk

- `[x]` Execution Guard token primitive.
- `[x]` MT5 bridge rejects order send without guard token.
- `[x]` MT5 bridge rejects order send before order check.
- `[x]` Live trading disabled by default.
- `[x]` Risk engine control-plane policy, persistent risk policies, and Execution Guard checks.
- `[x]` Kill switch module with global/scoped persistence, audit, deactivation, and Execution Guard blocking.
- `[x]` Governance scaffold with strategy lifecycle, approvals, permissions, live gate blocking, and deployment records.
- `[x]` Account permission check.
- `[x]` User permission check.
- `[x]` Strategy permission check.
- `[x]` Trading mode policy enforcement in Execution Guard control-plane check.
- `[x]` Max daily and weekly loss checks.
- `[x]` Max open trades and trades per day checks.
- `[!]` Spread and slippage checks from broker telemetry payload; direct live MT5 telemetry binding is held pending broker validation.
- `[!]` News halt integration as an Execution Guard input; adapter is deployed and fail-safe, final execution-time binding is held pending provider configuration and demo execution workflow.
- `[x]` Duplicate trade risk detection as an Execution Guard input using open-position and pending-signal matching.
- `[!]` Margin availability validation as an Execution Guard input; live MT5 margin binding is held pending account-level validation.
- `[x]` Correlation exposure checks as an Execution Guard input using symbol currency exposure groups and configurable limits.
- `[!]` Broker compatibility enforcement through Execution Guard input; live broker checker pass is held pending broker metadata validation.
- `[x]` Market data quality enforcement inputs available from live MT5 candle/tick history and worker telemetry.
- `[x]` System health score execution gating.
- `[x]` Global and scoped kill switch API fully wired with persistent activation, listing, deactivation, audit logging, and Execution Guard blocking.
- `[x]` Runtime kill-switch drill completed against deployed services and deactivated after Execution Guard block verification.

## MT5 Bridge

- `[x]` FastAPI bridge service.
- `[x]` `/health` and `/metrics`.
- `[x]` `/account`, `/symbols`, `/rates/{symbol}`, `/ticks/{symbol}`.
- `[x]` `/order/check`, `/order/send`, `/positions`, `/history`.
- `[x]` Demo MT5 terminal detected.
- `[x]` Bridge token protection.
- `[x]` Windows scheduled task startup.
- `[x]` Multi-account terminal manager scaffold.
- `[!]` One MT5 terminal instance per account; software profile routing is ready, terminal launch orchestration is held until account list and terminal paths are confirmed.
- `[!]` Per-account bridge ports `8501+`; account route metadata and profile API are wired, multi-process launcher is held until multi-account terminal validation.
- `[x]` Account profile persistence without broker credentials.
- `[!]` Broker credential onboarding without secret leakage; profiles intentionally exclude credentials and onboarding is held for a secret-manager backed workflow.
- `[x]` Windows service mode alternative script.
- `[x]` Production MT5 bridge observability with safe `/observability`, per-profile gauges, checked-order gauges, and order_check/order_send counters and latency metrics.

## Strategy Registry And Governance

- `[x]` Strategy registry/plugin skeleton.
- `[x]` Lifecycle states documented and enforced in order.
- `[x]` Governance modules scaffolded.
- `[x]` Real JSON strategy plugin loader.
- `[x]` Strategy database.
- `[!]` Strategy approval workflow UI; API workflow and audit records are wired, richer dashboard controls are held for the next dashboard UX pass.
- `[x]` User/account/environment strategy permissions.
- `[x]` Backtest status gate defined in promotion workflow and demo validation report.
- `[x]` Forward test status gate defined in promotion workflow and demo validation report.
- `[x]` Demo validation gate and demo validation report endpoint.
- `[x]` Live approval gate blocks production-live unless super_admin live approval is recorded.
- `[!]` Rollback target captured in approval records; automated rollback execution is held pending operator-approved rollback runbooks.

## Backtest, Forward Test, And Tuning

- `[x]` Backtest, forward-test, and tuning route skeletons with persistent job records.
- `[x]` Agent skeletons.
- `[!]` Backtest engine; deterministic mock-safe scoring and historical candle storage are wired, full historical execution engine is held pending data depth and strategy rules.
- `[x]` Historical candle storage from market telemetry.
- `[x]` Forward-test scheduler records.
- `[!]` Walk-forward validation placeholder; validation execution is held pending historical data depth.
- `[x]` Parameter tuning job queue.
- `[!]` Overfitting detection placeholder in tuning results; statistical detection is held pending historical sample size.
- `[x]` Strategy leaderboard from quality scores.
- `[x]` Daily/weekend scheduled job definitions exposed through API.
- `[x]` Quality scoring implementation using requested 30/25/20/15/10 weighting.

## Market Data And News

- `[x]` Market worker service wrapper.
- `[x]` Market data quality checker scaffold and API analysis binding.
- `[x]` Broker compatibility checker scaffold.
- `[x]` Real candle/tick collector through MT5 bridge snapshots with durable candle storage.
- `[x]` Technical indicator engine with SMA, EMA, RSI, ATR, MACD, and Bollinger Band calculations from MT5 candle snapshots.
- `[x]` Multi-timeframe analyzer over persisted market snapshots.
- `[x]` Price action detector scaffold over latest market snapshot.
- `[x]` Spread/slippage monitor over persisted telemetry.
- `[x]` News/fundamental adapter implemented with reviewed JSON file and HTTPS JSON provider modes.
- `[!]` External news provider activation; held pending reviewed calendar file or approved provider URL/API key.
- `[x]` High-impact news halt logic defaults to safe halt unless provider is enabled and clear.
- `[!]` Stale feed detection available in market analysis and Execution Guard inputs; automatic execution-time binding is held pending demo execution workflow.

## Localization

- `[x]` Locale directories for English and Bahasa Melayu Malaysia.
- `[x]` Localization service scaffold.
- `[x]` Glossary file.
- `[x]` Tests for non-translation rules.
- `[x]` Dashboard language selector.
- `[!]` Full dashboard translation coverage; primary panels are API-localized, deeper admin forms are held for dashboard UX pass.
- `[!]` Notification translation coverage through locale files/templates; channel adapters are held pending live notification credentials.
- `[!]` Agent Theater translation coverage through rendered labels and selected safe summaries; full free-text translation adapter is held pending LLM translation policy.
- `[!]` Trade approval message translation coverage through templates; channel delivery adapter is held pending notification credentials.
- `[x]` Automatic language detection API for live user workflows.

## Notifications

- `[x]` Notification hub scaffold.
- `[x]` Escalation matrix documented and exposed through API.
- `[!]` Telegram integration readiness checks; delivery adapter is held pending token and live test.
- `[!]` WhatsApp Business Cloud API readiness checks; delivery adapter is held pending token and live test.
- `[!]` Mobile push readiness checks; delivery adapter is held pending FCM credentials and live test.
- `[!]` Email SMTP readiness checks; delivery adapter is held pending SMTP credentials and live test.
- `[!]` Browser push readiness checks; delivery adapter is held pending VAPID configuration.
- `[!]` Discord/SMS optional readiness checks; adapters are held pending credentials.
- `[x]` Quiet hours.
- `[!]` Approval/rejection workflows through notification event records; real channel callbacks are held pending notification credentials/webhooks.

## Paid And Local LLM Routing

- `[x]` Ollama installed with local model pulls.
- `[x]` Paid LLM gateway scaffold/mock mode.
- `[x]` LLM Cost Center scaffold with persisted usage records.
- `[x]` Model Evaluation Center scaffold with persisted evaluation records.
- `[!]` Production model router; safe route/approval/fallback logic is wired, real paid API calls are held until keys and approvals are configured.
- `[!]` OpenAI API integration readiness; held until `OPENAI_API_KEY` and paid-use approval are configured.
- `[!]` Gemini API integration readiness; held until `GEMINI_API_KEY` and paid-use approval are configured.
- `[x]` Cost budgets and approval thresholds enforced.
- `[x]` Secret redaction before paid LLM calls.
- `[x]` Fallback-to-local policy enforcement.
- `[x]` Model quality reports.

## OpenClaw Optional Gateway

- `[x]` OpenClaw gateway scaffold.
- `[x]` Disabled by default.
- `[x]` Allowed actions file.
- `[!]` Real OpenClaw bridge; safety API bridge exists, external OpenClaw runtime adapter is held until OpenClaw runtime is installed and reviewed.
- `[!]` Admin/user chat workflows through Orchestrator/Agent Theater; direct OpenClaw runtime chat adapter is held until OpenClaw runtime is approved.
- `[x]` Approval-only API action layer.
- `[x]` Safety policy tests.

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
- `[x]` Structured JSON API access logs in the control service; Agent Theater events continue to stream to Loki.
- `[x]` Docker/container metrics through cAdvisor on the control node and Grafana operations dashboard.
- `[x]` API request dashboards with request rate and p95 latency.
- `[x]` Worker/agent queue dashboards from database-backed Prometheus gauges.
- `[x]` Agent event dashboards through Agent Theater Loki and operations panels.
- `[!]` Trade/risk dashboards; kill-switch, risk-policy, stale-market, account, and approval gauges are live, full trade lifecycle dashboards are held until demo trade lifecycle exists.
- `[x]` Loki log ingestion from Docker/container services through Promtail.
- `[x]` Alert rules and notification routing through Prometheus Alertmanager webhook into Notification Hub.

## Backup, Restore, Deployment, Rollback

- `[x]` Backup/restore scripts scaffolded and hardened with checksums, private permissions, and restore confirmation gates.
- `[!]` Deployment/rollback scripts scaffolded; API release records persist backup points, test results, approvers, and rollback commands, but automated rollback execution is held for operator-approved runbooks.
- `[x]` Runtime secret rotation playbook.
- `[x]` GitHub source control and rollback base.
- `[x]` Scheduled backups through systemd timer on the control node.
- `[x]` Backup verification script and systemd timer.
- `[x]` Non-destructive restore drill script and service.
- `[!]` Deployment approval workflow; super-admin API gate and audit records are wired, richer dashboard approval UI is held for dashboard UX pass.
- `[x]` Release IDs, changelogs, approvers, rollback commands persisted.

## Mobile And External API Readiness

- `[x]` Mobile API contract docs.
- `[x]` Kotlin client example.
- `[x]` Mobile bootstrap route with environment, auth, WebSocket, feature, and latest account contract.
- `[x]` Authenticated push registration route with database-backed token hash records.
- `[!]` Real Android/iOS app held until mobile app build is explicitly requested.
- `[!]` FCM credentials and push sender held until FCM project credentials are configured.
- `[!]` Mobile 2FA; JWT login and TOTP backend are ready, mobile-specific screens/client flow held until app build.
- `[!]` Mobile approval/rejection flow; API records and mobile pending approval feed are wired, push delivery and MT5 execution handoff held pending notification credentials and demo execution flow.

## Production Readiness Gates Before Live Trading

- `[x]` Real user/account persistence.
- `[x]` Full RBAC and audit persistence.
- `[x]` Real risk policies per account.
- `[!]` Real strategy validation pipeline; plugin governance, lifecycle order, backtest/forward/tuning job records, permissions, historical candles, and demo report are wired, full historical execution engine is held pending data depth.
- `[x]` Demo trading validation report endpoint.
- `[x]` Manual approval workflow proven at API/database level; notification delivery and MT5 handoff remain gated until channel credentials and demo execution flow are proven.
- `[!]` Restricted live auto-trading reviewed and approved: held by safety policy.
- `[x]` Secret manager provider layer deployed with environment provider active; external providers held for operator selection.
- `[x]` Backup verification and non-destructive restore drill tooling deployed.
- `[x]` Monitoring alerts connected to notification hub.
- `[x]` Security review completed and recorded through audited pre-live API.
- `[x]` Broker compatibility checks passed for the currently connected demo bridge profile.
- `[x]` Market data quality gates passed for current monitored symbols with fresh MT5 tick/candle telemetry.
- `[x]` Kill switch tested at control-plane level and included in readiness gates.
- `[x]` Production-live environment explicitly approved through audited pre-live API.
- `[x]` Safe live runtime enable/disable automation documented in `docs/LIVE_TRADING_ENABLEMENT.md`.
