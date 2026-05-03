# FCM Push Setup

Required environment placeholders:

```bash
FCM_SERVER_KEY=<FCM_SERVER_KEY>
FCM_PROJECT_ID=<FCM_PROJECT_ID>
```

Current readiness:

- Mobile clients can register a device through `POST /api/v1/mobile/push/register`.
- Raw device push tokens are not returned by the API.
- Production push delivery remains disabled until FCM credentials are configured, encrypted token storage is approved, and a live test notification succeeds.

Set these values through environment variables or your secret manager only:

- `FCM_SERVER_KEY=<FCM_SERVER_KEY>`
- `FCM_PROJECT_ID=<FCM_PROJECT_ID>`
