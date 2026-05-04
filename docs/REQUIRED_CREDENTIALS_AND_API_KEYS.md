# Required Credentials And API Keys

This document lists every credential, token, API key, password, and external approval needed to operate the Forex AI Control Tower.

Never paste real secrets into chat, Git, Markdown, inventory files, scripts, Docker Compose files, Grafana dashboards, logs, or screenshots. Set them through environment variables or an approved secret manager only.

## Current Required Runtime Secrets

These are required for the deployed control tower baseline.

| Variable | Required for | Where used | Notes |
| --- | --- | --- | --- |
| `POSTGRES_PASSWORD` | PostgreSQL application access | Control API, worker services, backup jobs | Rotate if exposed. |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin login | Grafana container/runtime | Set once, then change through Grafana UI if desired. |
| `JWT_SECRET_KEY` | API login/session tokens | Control API | Use a long random value. Rotation invalidates active sessions. |
| `EXECUTION_GUARD_SIGNING_KEY` | Execution Guard approval token signing | Control API, guarded execution flow | Required before any MT5 order handoff. |
| `BRIDGE_API_TOKEN` | MT5 bridge API authentication | Workers, control API, MT5 bridge | Already rotated once; keep it private. |

## Controller And Deployment Access

These are required for controller-driven deployment and GitHub source control.

| Variable | Required for | Where used | Notes |
| --- | --- | --- | --- |
| `GITHUB_OWNER` | GitHub repo setup | GitHub setup script | Account or organization owner. |
| `GITHUB_REPO` | GitHub repo setup | GitHub setup script | Usually `forex-ai-control-tower`. |
| `GITHUB_TOKEN` | GitHub repo creation/push | GitHub REST/Git remote auth | Needs repo scope. Never print it. |
| `LINUX_STANDARD_SSH_PASSWORD` | Linux host SSH bootstrap | Ansible inventory | Used for machines 1-5. |
| `LINUX_STANDARD_SUDO_PASSWORD` | Linux privilege escalation | Ansible inventory | Used for machines 1-5. |
| `WINDOWS_MT5_USER` | Windows MT5 bridge login | WinRM/OpenSSH inventory | Username only, not secret. |
| `WINDOWS_MT5_PASSWORD` | Windows WinRM auth | Windows playbooks | Use only through env/secret manager. |
| `WINDOWS_MT5_SSH_PASSWORD` | Windows OpenSSH fallback auth | Fallback scripts/playbooks | Only needed for SSH fallback. |

## News And Fundamental Data

FMP is the currently configured live provider.

| Variable | Required for | Where used | Notes |
| --- | --- | --- | --- |
| `NEWS_PROVIDER_TYPE=fmp_economic_calendar` | FMP calendar provider | Control API news adapter | Active provider mode. |
| `NEWS_PROVIDER_API_KEY` | FMP API access | Control API news adapter | Keep out of URLs and docs. The adapter builds the request internally. |
| `NEWS_HIGH_IMPACT_WINDOW_MINUTES` | News halt window | Execution Guard/news status | Default `45`. |
| `NEWS_STALE_AFTER_MINUTES` | Provider freshness gate | News status | Default `720`. |
| `NEWS_CALENDAR_FROM` | Optional FMP query window | News adapter | Optional `YYYY-MM-DD`. |
| `NEWS_CALENDAR_TO` | Optional FMP query window | News adapter | Optional `YYYY-MM-DD`. |

Alternative provider modes:

| Variable | Required for | Notes |
| --- | --- | --- |
| `NEWS_PROVIDER_TYPE=manual_json` | Reviewed local calendar file | Use `NEWS_CALENDAR_SOURCE_FILE` from the controller, copied safely to the control node. |
| `NEWS_PROVIDER_TYPE=https_json` | Approved HTTPS JSON endpoint | Use `NEWS_CALENDAR_URL`; if a key is needed, use `NEWS_PROVIDER_API_KEY`. |

## Notifications And Approval Delivery

At least one reliable admin channel is required before real manual approval-to-execution workflows should be activated.

| Variable | Channel | Required for | Notes |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Telegram | Approval requests, alerts | Recommended first notification channel. |
| `TELEGRAM_ADMIN_CHAT_ID` | Telegram | Admin delivery target | Chat ID is sensitive operational metadata; keep private. |
| `WHATSAPP_TOKEN` | WhatsApp Business Cloud API | Critical/emergency alerts | Needs Meta app and approved phone number. |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business Cloud API | Sending messages | Pair with `WHATSAPP_TOKEN`. |
| `SMTP_HOST` | Email | Email reports/critical alerts | Hostname only. |
| `SMTP_PORT` | Email | Email delivery | Common values: `587` or `465`. |
| `SMTP_USER` | Email | SMTP login | Often an email address. |
| `SMTP_PASSWORD` | Email | SMTP login | Use app password where possible. |
| `SMTP_FROM` | Email | Sender identity | Example: `alerts@your-domain`. |
| `FCM_PROJECT_ID` | Mobile push | Android/iOS push | Required for mobile push sender. |
| `FCM_SERVER_KEY` or `FCM_SERVICE_ACCOUNT_JSON` | Mobile push | FCM authentication | Prefer service account JSON through secret manager. |
| `VAPID_PUBLIC_KEY` | Browser push | Browser notification registration | Public but still manage consistently. |
| `VAPID_PRIVATE_KEY` | Browser push | Browser push signing | Secret. |
| `DISCORD_WEBHOOK_URL` | Discord optional | Optional alert mirror | Treat as secret. |
| `SMS_PROVIDER_TOKEN` | SMS optional | Emergency fallback | Provider-specific. |

## Paid LLM Providers

Paid providers must be budgeted and approved before use. Local Ollama remains the default fallback.

| Variable | Provider | Required for | Notes |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI | GPT-5 family routing | Set spend limits before enabling paid calls. |
| `GEMINI_API_KEY` | Google Gemini | Gemini Pro family routing | Set spend limits before enabling paid calls. |
| `LLM_DAILY_BUDGET_USD` | Cost Center | Daily spend guard | Required before paid routing. |
| `LLM_MONTHLY_BUDGET_USD` | Cost Center | Monthly spend guard | Required before paid routing. |
| `PAID_LLM_APPROVAL_REQUIRED` | Governance | Approval gate | Keep `true` in production. |

## MT5 And Broker Operations

Broker credentials must not be stored in repo files. The currently connected MT5 demo terminal is already logged in manually.

| Secret or input | Required for | Notes |
| --- | --- | --- |
| MT5 demo account login/password/server | Demo account onboarding | Prefer manual MT5 login or secret manager injection. |
| MT5 live account login/password/server | Live account onboarding | Do not configure until live approval record exists. |
| Per-account terminal path | Multi-account routing | Needed for one MT5 terminal per account. |
| Per-account bridge port | Multi-account routing | Example: `8501`, `8502`, `8503`. |
| Broker symbol suffix/prefix map | Broker compatibility | Needed when broker uses symbols like `EURUSDm`. |

## Security, Auth, And Recovery

| Variable | Required for | Notes |
| --- | --- | --- |
| `LOCAL_AUTH_BOOTSTRAP_ENABLED` | First admin bootstrap | Use temporarily only. Disable after admin user exists. |
| `LOCAL_ADMIN_BOOTSTRAP_PASSWORD` | First admin bootstrap | Temporary only; rotate/remove after use. |
| `TOTP_ISSUER` | 2FA | Display name in authenticator apps. |
| `RECOVERY_EMAIL` | Password recovery/contact | Current requested recovery email: configure through app settings, not source code. |
| `ALERTMANAGER_WEBHOOK_TOKEN` | Monitoring webhook auth | Optional if webhook is restricted to tower private subnet. |

## OpenClaw Optional Layer

OpenClaw must remain human-facing only. It cannot send orders, read broker passwords, bypass the risk engine, run unrestricted shell commands, or modify production directly.

| Variable | Required for | Notes |
| --- | --- | --- |
| `OPENCLAW_ENABLED=false` | Safe default | Keep false until runtime review. |
| `OPENCLAW_API_URL` | Optional bridge | Only after OpenClaw is installed and reviewed. |
| `OPENCLAW_API_TOKEN` | Optional bridge auth | Secret; store in env/secret manager only. |

## Recommended Setup Order

1. Runtime core: `POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `JWT_SECRET_KEY`, `EXECUTION_GUARD_SIGNING_KEY`, `BRIDGE_API_TOKEN`.
2. News: `NEWS_PROVIDER_TYPE=fmp_economic_calendar`, `NEWS_PROVIDER_API_KEY`.
3. Admin notification: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`.
4. Email fallback: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
5. Mobile push: `FCM_PROJECT_ID`, FCM credential.
6. Paid LLM: `OPENAI_API_KEY`, `GEMINI_API_KEY`, budget variables, governance approval.
7. Multi-account MT5: account list, terminal paths, bridge ports, broker symbol maps.
8. Optional WhatsApp/SMS/Discord/OpenClaw after core safety flow is proven.

## Validation Commands

Use these commands without printing secret values:

```powershell
Set-Location E:\codex\fx-ai-tower\forex-ai-control-tower

docker compose -f docker/controller-runner.compose.yml run --rm controller `
  ansible-playbook -i ansible/inventory.yml ansible/playbooks/production_runtime.yml --limit control

Invoke-RestMethod "http://10.10.1.81:8000/health"
Invoke-RestMethod "http://10.10.1.81:8000/api/v1/news/status?symbol=EURUSD"
Invoke-RestMethod "http://10.10.1.81:8000/api/v1/notifications/channels/status"
```

## Reboot Persistence Note

The current safe deployment model passes secrets through environment variables and avoids committing or writing them to plaintext files. Some `systemctl set-environment` values are runtime-scoped and may need to be re-applied after reboot unless a secret manager is configured.

Before relying on unattended reboot recovery for production-live mode, choose and configure one of:

- HashiCorp Vault.
- SOPS with age-encrypted secret files.
- A cloud secret manager.
- A dedicated host-level secret injection mechanism approved in `docs/secret_manager_integration.md`.

