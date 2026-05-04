# News Adapter

The News Impact Agent uses the control API news adapter to decide whether news-sensitive strategies should be halted.

Default behavior is fail-safe:

- `NEWS_PROVIDER_ENABLED=false` keeps `news_halt_active=true`.
- A missing, stale, invalid, or unhealthy provider keeps `news_halt_active=true`.
- A high-impact event inside the halt window keeps `news_halt_active=true`.

## Provider Modes

### Reviewed JSON File

Use this for the first production-safe rollout because the calendar can be reviewed before deployment.

```powershell
Set-Item -Path Env:NEWS_PROVIDER_ENABLED -Value 'true'
Set-Item -Path Env:NEWS_PROVIDER_TYPE -Value 'manual_json'
Set-Item -Path Env:NEWS_CALENDAR_FILE -Value '<absolute path to reviewed calendar JSON>'
```

Expected JSON shape is shown in `configs/news_calendar.example.json`.

### HTTPS JSON Provider

Use this only after the provider contract is reviewed.

```powershell
Set-Item -Path Env:NEWS_PROVIDER_ENABLED -Value 'true'
Set-Item -Path Env:NEWS_PROVIDER_TYPE -Value 'https_json'
Set-Item -Path Env:NEWS_CALENDAR_URL -Value '<approved HTTPS calendar endpoint>'
```

If the provider requires an API key, set `NEWS_PROVIDER_API_KEY` through the approved environment or secret manager. Do not commit it.

### Financial Modeling Prep Economic Calendar

Use this for the free/low-friction calendar feed. The API key stays in `NEWS_PROVIDER_API_KEY`; do not place it in `NEWS_CALENDAR_URL` and do not paste it into documentation or Git.

```powershell
Set-Location E:\codex\fx-ai-tower\forex-ai-control-tower
$env:NEWS_PROVIDER_TYPE = 'fmp_economic_calendar'
$env:NEWS_PROVIDER_API_KEY = '<set locally only, do not commit>'
$env:NEWS_HIGH_IMPACT_WINDOW_MINUTES = '45'
$env:NEWS_STALE_AFTER_MINUTES = '720'

docker compose -f docker/controller-runner.compose.yml run --rm controller `
  ansible-playbook -i ansible/inventory.yml ansible/playbooks/news_provider_config.yml --limit control
```

Optional date window:

```powershell
$env:NEWS_CALENDAR_FROM = '2026-05-04'
$env:NEWS_CALENDAR_TO = '2026-05-11'
```

If the provider is unavailable, stale, or returns no usable events, the tower remains in `news_safe_mode`.

## Controls

- `NEWS_HIGH_IMPACT_WINDOW_MINUTES`: default `45`.
- `NEWS_STALE_AFTER_MINUTES`: default `720`.

## Verification

```powershell
Invoke-RestMethod 'http://10.10.1.81:8000/api/v1/news/status?symbol=EURUSD'
Invoke-RestMethod 'http://10.10.1.81:8000/api/v1/news/events?symbol=EURUSD'
```

Agent Theater will show the News Agent as connected only when the provider is enabled, fresh, and readable.
