# OpenClaw Integration Plan

OpenClaw is disabled by default and may only act as a human-facing assistant layer.

## Deployment Sequence

1. Keep `OPENCLAW_ENABLED=false` until governance review is complete.
2. Configure `OPENCLAW_API_URL` and `OPENCLAW_API_TOKEN` in Credentials dashboard (OpenClaw category).
3. Enable `OPENCLAW_ENABLED=true`.
4. Verify `GET /api/v1/openclaw/status` returns:
   - `enabled=true`
   - `runtime_configured=true`
5. Run controlled tests:
   - `POST /api/v1/openclaw/actions/check`
   - `POST /api/v1/openclaw/chat`
   - `POST /api/v1/openclaw/status/query`
   - `POST /api/v1/openclaw/summary/daily`
   - `POST /api/v1/openclaw/api-call` (whitelisted path only)
   - `GET /api/v1/openclaw/runtime/health`
   - `GET /api/v1/openclaw/contract`

## Current Runtime Baseline (Active)

- Runtime service: `forex-openclaw-runtime` (systemd on `fx-control`)
- Runtime URL: `http://10.10.1.81:8600`
- Gateway URL: `http://10.10.1.81:8000/api/v1/openclaw`
- Status verification:
  - `GET /api/v1/openclaw/status` shows `runtime_configured=true`
  - `GET http://10.10.1.81:8600/health` returns runtime health
  - `GET /api/v1/openclaw/runtime/health` shows runtime probe and timezone-aware runtime timestamp
  - `GET /api/v1/openclaw/contract` shows allowed actions/targets/approved read-only paths

## Hard Restrictions (must remain true)

- OpenClaw cannot execute trades.
- OpenClaw cannot read broker passwords.
- OpenClaw cannot bypass Execution Guard or approval workflow.
- OpenClaw cannot run shell commands.
- OpenClaw cannot mutate production directly.

## Orchestrator AI Provider Routing

- `ORCHESTRATOR_GENERAL_CHAT_MODE=auto|openai|local|disabled`
- Primary provider: OpenAI API (`OPENAI_API_KEY`)
- Fallback provider: local LLM (`OLLAMA_REASON_URL`, `LOCAL_LLM_API_STYLE`, `ORCHESTRATOR_GENERAL_CHAT_MODEL`)
- Disabled mode: no LLM calls; safe deterministic status/routing responses only.

Security boundary:

- ChatGPT website login automation and browser session scraping are not supported backend integrations.
- Use API keys/secrets through credential manager only.
