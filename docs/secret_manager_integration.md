# Secret Manager Integration

The control tower reads secrets from environment variables by default. This is production-safe for the current controller-driven deployment because secrets are not committed, echoed, or written to inventory files.

For reboot-persistent production operations, choose one external provider before enabling live trading:

- HashiCorp Vault: set `VAULT_ADDR` and `VAULT_TOKEN`, then map paths under `secret/data/forex-ai-control-tower`.
- SOPS with age: keep only encrypted files under `secrets/`, which remains ignored by git.
- Cloud secret manager: use your cloud provider and expose resolved values as environment variables at service start.

Required runtime secrets:

- `POSTGRES_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- `JWT_SECRET_KEY`
- `EXECUTION_GUARD_SIGNING_KEY`
- `BRIDGE_API_TOKEN`

Optional local-auth bootstrap:

- `LOCAL_AUTH_BOOTSTRAP_ENABLED=true`
- `LOCAL_ADMIN_BOOTSTRAP_PASSWORD=<temporary-admin-password>`

After bootstrap, unset `LOCAL_AUTH_BOOTSTRAP_ENABLED` and rotate/remove the temporary password.
