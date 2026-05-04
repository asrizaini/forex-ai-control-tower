# Laravel Dashboard Plan

Laravel is a good fit for the operator/admin dashboard, especially for forms, approval workflows, user management, audit views, and long-lived server-rendered pages. The trading control plane should remain in FastAPI because it already owns Execution Guard, MT5 bridge integration, audit logging, WebSocket streams, and safety gates.

## Recommended Architecture

- FastAPI remains the canonical API and trading safety boundary.
- Laravel runs as a separate dashboard console and consumes FastAPI over REST/WebSocket.
- Laravel does not connect directly to MT5, broker credentials, PostgreSQL trading tables, or secret stores.
- Laravel approval actions call audited FastAPI endpoints only.
- Grafana remains observability-first; Laravel becomes operator workflow-first.

## Migration Path

1. Keep the existing React/Vite dashboard running on port `5173`.
2. Build Laravel dashboard in parallel under `control/dashboard-laravel`.
3. Add Laravel read-only panels first: readiness, health, market feed, Agent Theater links.
4. Add authenticated Laravel login against FastAPI `/api/v1/auth/login`.
5. Add audited pre-live forms for security review and production-live approval.
6. Add strategy governance, users, accounts, risk policy, approvals, notifications, and reports.
7. Cut traffic from React to Laravel only after parity checks pass.

## Safety Rules

- No live trading action can be implemented only in Laravel.
- Laravel must not store broker credentials or API tokens.
- Laravel must not bypass Execution Guard, Risk Manager, or FastAPI audit.
- Production-live buttons stay disabled until authenticated JWT and explicit confirmation flows are wired.

## Current Scaffold

The first Laravel scaffold is deployed on `10.10.1.81:8090` as a read-first operator console. It displays:

- API health.
- Production readiness gates.
- Next required actions.
- Recent market feed snapshots.
- Links to FastAPI docs and Grafana.

The live action buttons are intentionally disabled until Laravel authentication and audited POST workflows are implemented. Production-live remains controlled by the FastAPI readiness gates and the guarded Ansible enablement playbook.
