# Forex AI Control Tower Laravel Dashboard

This is the optional Laravel operator console for the Forex AI Control Tower.

FastAPI remains the canonical trading/control API. Laravel consumes FastAPI and must not bypass:

- Execution Guard
- Risk Manager
- audit logging
- production-live approval gates
- MT5 bridge token protection

## Local Preview

```powershell
composer install
$env:APP_KEY='base64:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
$env:CACHE_STORE='file'
$env:SESSION_DRIVER='file'
$env:QUEUE_CONNECTION='sync'
$env:CONTROL_TOWER_API_URL='http://10.10.1.81:8000'
php artisan serve --host=0.0.0.0 --port=8090
```

Open `http://127.0.0.1:8090`.

## Current Scope

- Read-only API health panel.
- Read-only pre-live gate panel.
- Read-only market feed table.
- Links to FastAPI docs and Grafana.
- Disabled live approval buttons until Laravel authentication and audited FastAPI POST workflows are wired.

No secrets belong in this dashboard repository. Use `.env` only for local runtime settings, and never commit it.
