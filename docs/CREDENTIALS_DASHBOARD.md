# Credentials And Configuration Dashboard

The fx-control dashboard now owns ongoing credential and runtime configuration management after deployment. Codex or the controller computer should only be needed for initial deployment, planned maintenance, source updates, and break-glass recovery.

## Access

Open the primary Laravel control dashboard:

`http://10.10.1.81:5173`

Log in with an admin account, then use the **Control Plane** area and **Credentials Center**.

## What It Does

- Lists required credentials, tokens, API keys, passwords, and service configuration values.
- Shows configured, missing, and invalid status without exposing secret values.
- Supports save/update for each value.
- Supports auto-generation for internal keys and tokens where applicable.
- Supports explicit show/reveal and copy actions for operators who have admin permission.
- Writes audit records for save, generate, and reveal actions without recording secret values.
- Stores sensitive values encrypted on the fx-control machine.

## Storage

Sensitive values are encrypted before being stored in the control database. The encryption key is kept on fx-control at:

`/etc/forex-ai-control-tower/credential_store.key`

The file is owned by `root:aiops` and readable by the API service group only. Do not copy it into Git, chat, screenshots, dashboards, logs, or tickets.

## Security Rules

- Normal API responses return only masked secret values.
- A full value is returned only from the explicit reveal action and only for an authenticated admin.
- Audit logs record which field changed, who changed it, and whether a value is configured, but never the secret value.
- Generated values are shown once so the operator can save or place them in the external service that needs them.
- If a value is exposed in chat, logs, screenshots, or commits, rotate it immediately.

## Bootstrap Notes

The API still needs its boot credentials to start safely after reboot, including database access and JWT signing. Those values are already persisted on fx-control by the production runtime deployment. The dashboard is now the operator-facing source for updating and validating ongoing credentials such as FMP, Telegram, WhatsApp, FCM, SMTP, broker bridge tokens, LLM keys, notification providers, and trading configuration values.

For changes that affect a service at process startup, update the value in the dashboard, then use the deployment/runtime apply workflow to restart the relevant service during a maintenance window.

## Health Page

The control API exposes:

`GET /api/v1/system/health/status`

This reports API, database, Grafana, Prometheus, Qdrant, Loki, and required credential status. The dashboard consumes this status for operator visibility.
