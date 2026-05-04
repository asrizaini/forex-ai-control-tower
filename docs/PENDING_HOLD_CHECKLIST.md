# Pending Hold Checklist

This checklist contains roadmap items that should not be marked complete until external credentials, broker validation, live data depth, operator review, or explicit product scope is available. These are holds, not forgotten work.

## Trading Safety Holds

- `[!]` Restricted live auto-trading review and approval.
  - Reason: Live automation must remain disabled until demo validation, security review, kill-switch drill, broker checks, and explicit production-live approval all pass.
  - Solution: Run demo-only approval-to-MT5 workflow for at least one full validation cycle, export reports, complete sign-off, then enable only `restricted_live_auto` with account-specific limits.

- `[!]` Manual approval to MT5 handoff.
  - Reason: Approval records exist, but the final guarded handoff to MT5 must be proven in demo mode.
  - Solution: Create demo approval request, run Execution Guard check, pass `order_check`, send demo order only, verify journal/audit/notification records, then document result.

## Broker And MT5 Holds

- `[!]` One MT5 terminal per account and per-account ports.
  - Reason: Account profile routing exists, but terminal paths, account list, and multi-process launch behavior must be verified on Windows.
  - Solution: Define account profiles without credentials, assign port map `8501+`, launch separate terminals, verify `/health`, `/account`, `/symbols`, `/order/check` per profile.

- `[!]` Broker credential onboarding.
  - Reason: Credentials must never be committed or stored in plaintext profiles.
  - Solution: Choose Vault, SOPS, or cloud secret manager; store broker credentials there; MT5 bridge reads at runtime only; test redaction.

## Market Data And Strategy Holds

- `[!]` External news/fundamental provider configuration.
  - Reason: The adapter is implemented and deployed, but no approved calendar file or HTTPS provider URL is configured yet.
  - Solution: Provide a reviewed `NEWS_CALENDAR_SOURCE_FILE` for `manual_json`, or set an approved `NEWS_CALENDAR_URL` and optional `NEWS_PROVIDER_API_KEY` for `https_json`, then run `ansible/playbooks/news_provider_config.yml`.

- `[!]` Full historical backtest execution engine.
  - Reason: Historical candle storage now exists, but enough history and strategy-specific execution rules are required.
  - Solution: Collect/import historical candles, define spread/slippage assumptions, implement fills, commissions/swaps, walk-forward validation, and overfitting detection.

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
