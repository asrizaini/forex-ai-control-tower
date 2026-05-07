# OpenClaw Gateway

OpenClaw is optional, disabled by default, and permanently forbidden from direct MT5 execution.

## Safety Guarantees

- No direct trade execution.
- No broker secret access.
- No risk/admin-approval bypass.
- No unrestricted shell command path.
- Only approved human-facing actions are allowed.
- All gateway actions are audited.

## Implemented Gateway Actions

- `admin_chat`
- `user_chat`
- `daily_summaries`
- `status_queries`
- `approved_api_calls` (read-only whitelist only)

## API Endpoints

- `GET /api/v1/openclaw`
- `GET /api/v1/openclaw/status`
- `POST /api/v1/openclaw/actions/check`
- `POST /api/v1/openclaw/chat`
- `POST /api/v1/openclaw/status/query`
- `POST /api/v1/openclaw/summary/daily`
- `POST /api/v1/openclaw/api-call`

## Runtime Modes

- **Local safe fallback**: active when `OPENCLAW_API_URL` is not configured.
- **External runtime forwarding**: enabled only when `OPENCLAW_ENABLED=true` and `OPENCLAW_API_URL` is configured.

Forwarded runtime calls remain policy-gated and cannot enable MT5 execution.
