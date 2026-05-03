# Android API Contract

Base path: `/api/v1`

Required mobile use cases: login with 2FA, account summary, active signals, approve/reject trades, open trades, risk status, push notifications, Agent Theater summaries, language setting, and notification preferences.

Implemented readiness endpoints:

- `GET /api/v1/mobile/bootstrap`
- `GET /api/v1/mobile/summary`
- `POST /api/v1/mobile/push/register`
- `GET /api/v1/mobile/push/registrations`

Push registration requires JWT authentication. The API stores a token hash only until the production FCM sender and encrypted token storage are enabled.
