# Pending Hold Checklist

This checklist contains roadmap items that should not be marked complete until external credentials, broker validation, live data depth, operator review, or explicit product scope is available. These are holds, not forgotten work.

## Trading Safety Holds

- `[!]` Restricted live auto-trading review and approval.
  - Reason: Live automation must remain disabled until demo validation, security review, kill-switch drill, broker checks, and explicit production-live approval all pass.
  - Solution: Run demo-only approval-to-MT5 workflow for at least one full validation cycle, export reports, complete sign-off, then enable only `restricted_live_auto` with account-specific limits.

- `[!]` Production-live environment approval.
  - Reason: The system must never default to production-live and cannot self-approve live trading.
  - Solution: Create a super-admin deployment/live-mode approval record, attach backup point, security review, broker compatibility report, market data quality report, and rollback command.

- `[!]` Manual approval to MT5 handoff.
  - Reason: Approval records exist, but the final guarded handoff to MT5 must be proven in demo mode.
  - Solution: Create demo approval request, run Execution Guard check, pass `order_check`, send demo order only, verify journal/audit/notification records, then document result.

- `[!]` Kill switch runtime drill.
  - Reason: API and Execution Guard blocking are implemented, but an operator-approved runtime drill should be performed against the live deployed services.
  - Solution: Activate global demo kill switch, verify approval/execution blocks, verify Agent Theater and notification alert, then deactivate and archive audit logs.

## Broker And MT5 Holds

- `[!]` One MT5 terminal per account and per-account ports.
  - Reason: Account profile routing exists, but terminal paths, account list, and multi-process launch behavior must be verified on Windows.
  - Solution: Define account profiles without credentials, assign port map `8501+`, launch separate terminals, verify `/health`, `/account`, `/symbols`, `/order/check` per profile.

- `[!]` Broker credential onboarding.
  - Reason: Credentials must never be committed or stored in plaintext profiles.
  - Solution: Choose Vault, SOPS, or cloud secret manager; store broker credentials there; MT5 bridge reads at runtime only; test redaction.

- `[!]` Broker compatibility pass.
  - Reason: Symbol suffixes, lot sizes, stop levels, margin, hours, and execution mode are broker-specific.
  - Solution: Pull broker metadata through MT5, run compatibility checker for each account/strategy/symbol, persist report, block unsafe combinations.

- `[!]` Detailed MT5 bridge observability.
  - Reason: Current health covers bridge/profile basics; per-terminal process/account metrics need multi-terminal mode.
  - Solution: Add per-profile metrics labels for terminal status, account login mask, symbol availability, last tick age, order_check latency, and bridge errors.

## Market Data And Strategy Holds

- `[!]` External news/fundamental feed.
  - Reason: No approved provider/API credentials are configured.
  - Solution: Choose provider, configure key in environment/secret manager, implement adapter, run high-impact news halt tests, audit all feed decisions.

- `[!]` Full technical indicator suite.
  - Reason: The current engine has short-term trend and quality summaries; final indicators depend on chosen strategies.
  - Solution: For each approved strategy, list exact indicators/timeframes, implement deterministic calculations, test against known candle samples.

- `[!]` Full historical backtest execution engine.
  - Reason: Historical candle storage now exists, but enough history and strategy-specific execution rules are required.
  - Solution: Collect/import historical candles, define spread/slippage assumptions, implement fills, commissions/swaps, walk-forward validation, and overfitting detection.

- `[!]` Market data quality gate pass.
  - Reason: Quality checks exist but must see enough live candle/tick history.
  - Solution: Run market worker long enough to collect required history, verify missing candles, stale ticks, abnormal spread, and frozen-feed checks pass per symbol.

- `[!]` Correlation exposure and duplicate trade matching.
  - Reason: Needs actual open positions, pending signals, and account grouping.
  - Solution: Persist positions/signals, map correlated symbols, define max exposure rules, then wire checks into Execution Guard request builder.

## Notification And Mobile Holds

- `[!]` Telegram, WhatsApp, email, browser push, Discord, SMS delivery adapters.
  - Reason: Credentials and live callback/webhook testing are not configured.
  - Solution: Add channel credentials via environment/secret manager, implement sender adapters, run live test per channel, record delivery/audit events.

- `[!]` FCM push sender.
  - Reason: Mobile push registration exists, but FCM credentials are not configured.
  - Solution: Configure `FCM_PROJECT_ID` and FCM credentials, implement sender, test critical alert delivery to a registered demo device.

- `[!]` Real Android/iOS app and mobile 2FA screens.
  - Reason: Mobile app build was explicitly out of scope for the current scaffold.
  - Solution: Use `mobile/android_api_contract.md` and `mobile/screen_flow.md` to build the app, then test login, TOTP, account summary, approvals, push, and language settings.

## LLM And OpenClaw Holds

- `[!]` Paid OpenAI/Gemini calls.
  - Reason: Paid providers must be budgeted, approved, and secrets must be configured without exposure.
  - Solution: Configure keys through secret manager, set daily/monthly budgets, require approval above threshold, run mock-to-paid comparison tests.

- `[!]` External OpenClaw runtime bridge.
  - Reason: OpenClaw is optional and disabled by default; runtime is not installed/reviewed here.
  - Solution: Install reviewed OpenClaw runtime, allow only approved human-facing actions, test no shell/trade/secret access, keep MT5 execution forbidden.

## Dashboard And UX Holds

- `[!]` Rich strategy approval dashboard controls.
  - Reason: API workflow exists, but UX needs operator design and safe review flows.
  - Solution: Add strategy lifecycle board, approval forms, backtest/forward/demo report views, rollback target selection, and audit preview.

- `[!]` Full dashboard/admin localization.
  - Reason: Primary panels are localized; deeper forms need complete copy review in Bahasa Melayu Malaysia.
  - Solution: Inventory every dashboard string, add locale keys, review Malaysian Malay wording, and test no code/config/secret terms are translated.

- `[!]` Trade lifecycle dashboards.
  - Reason: No real demo trade lifecycle has been executed yet.
  - Solution: After demo order workflow, add panels for approval, order_check, order_send, positions, journal, slippage, P/L, and post-trade review.

## Operations Holds

- `[!]` Automated rollback execution.
  - Reason: Release records and rollback commands exist, but automatic rollback can be destructive.
  - Solution: Create approved rollback runbooks per component, test in staging/demo, require backup verification and explicit approver before execution.
