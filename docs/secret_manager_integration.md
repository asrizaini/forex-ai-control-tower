# Secret Manager Integration

The control tower reads secrets from environment variables by default. This is production-safe for the current controller-driven deployment because secrets are not committed, echoed, or written to inventory files.

For reboot-persistent production operations, the prepared low-friction path is:

- Fill `secrets/control_tower_credentials.env` from `docs/control_tower_credentials.env.template`.
- Optionally encrypt it with Ansible Vault.
- Run `scripts/deploy_persistent_secrets.ps1`.

This installs root-only runtime secret files on Linux and machine-level environment variables on Windows. Services then survive reboot without the controller process exporting runtime secrets.

For larger production environments, choose one external provider before enabling unattended production-live operations:

- HashiCorp Vault: set `VAULT_ADDR` and `VAULT_TOKEN`, then map paths under `secret/data/forex-ai-control-tower`.
- SOPS with age: keep only encrypted files under `secrets/`, which remains ignored by git.
- Cloud secret manager: use your cloud provider and expose resolved values as environment variables at service start.

Required runtime secrets:

- `POSTGRES_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- `JWT_SECRET_KEY`
- `EXECUTION_GUARD_SIGNING_KEY`
- `BRIDGE_API_TOKEN`
- `NEWS_PROVIDER_API_KEY` when using `NEWS_PROVIDER_TYPE=fmp_economic_calendar`

Optional local-auth bootstrap:

- `LOCAL_AUTH_BOOTSTRAP_ENABLED=true`
- `LOCAL_ADMIN_BOOTSTRAP_PASSWORD=<temporary-admin-password>`

After bootstrap, unset `LOCAL_AUTH_BOOTSTRAP_ENABLED` and rotate/remove the temporary password.

See `docs/REQUIRED_CREDENTIALS_AND_API_KEYS.md` for the full credential inventory and recommended setup order.
