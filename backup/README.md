# Backup And Restore

Backups are designed for the control node and read secrets only from environment variables.

- `backup_postgres.sh` writes a custom-format PostgreSQL dump and checksum.
- `backup_configs.sh` archives deployable app/config files while excluding `.env`, secrets, keys, logs, and backup data.
- `backup_all.sh` runs both and writes a manifest.
- `verify_backup.sh` validates checksums and verifies both archive formats.
- Restore scripts require `RESTORE_CONFIRM=YES` and explicit restore file paths.

Default backup root:

```bash
/opt/forex-ai-control-tower/backups
```

The scheduled systemd timer installed by `ansible/playbooks/backup_schedule.yml` runs daily. Production-live changes should also trigger an on-demand backup before deployment, strategy promotion, live mode changes, or risk policy changes.
