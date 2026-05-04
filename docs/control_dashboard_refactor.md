# fx-control Dashboard Refactor

This release moves the Laravel operator dashboard from a single long page into routed operational pages:

- Overview / Home
- Credentials & Secrets
- Data Sources
- Economic Calendar
- News
- Alert Rules
- Workers / Agents
- Technical Analysis
- Fundamental Analysis
- Grafana / Monitoring
- API Status
- Logs & Audit
- Settings

## Calendar And News Architecture

The control API now stores and exposes normalized operational models for:

- data source configuration
- calendar events
- news items
- alert rules
- alert delivery history
- worker status
- worker runs
- analysis snapshots
- settings
- audit logs

Calendar/news providers use an adapter contract. The initial registered providers are:

- `forex_factory`
- `market_calendar_tool`
- `forex_factory_scrapper_api`
- `fmp`

Provider design follows these concepts:

- normalized internal event schema
- source priority and fallback
- currency and impact filtering
- timezone-aware event handling
- scrape status per source
- retry/backoff/rate-limit configuration
- pagination for calendar/news APIs
- alert rules for currency, impact, keywords, exact names, weekdays, source, and pairs

Direct website scraping remains disabled until an operator explicitly enables and configures a compliant runtime. This keeps the default deployment conservative and avoids aggressive scraping.

## Runtime Configuration Principle

After deployment, normal operations should be handled from the fx-control dashboard:

- credentials in Credentials & Secrets
- source priority and filters in Data Sources
- global timezone and intervals in Settings
- workers in Workers / Agents
- status in API Status and Grafana / Monitoring

Codex/control host usage should be limited to development, maintenance, or deployment automation.
