# Deployment And Rollback

Every deployment needs an ID, version, changelog, backup point, test result, approver, and rollback command.

The control API persists these records under `/api/v1/deployments/records`.

Rules:

- `production-live` cannot be created unless tests are marked `passed`.
- Rollback plans expose the rollback command and backup point, but execution remains an admin action.
- Deployment records are audited.
- Backup verification should pass before any status becomes `deployed`.
