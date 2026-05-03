#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_ROOT="${BACKUP_ROOT:-/opt/forex-ai-control-tower/backups}"
POSTGRES_BACKUP="${POSTGRES_BACKUP_FILE:-$BACKUP_ROOT/postgres/latest.dump}"
POSTGRES_MANIFEST="${POSTGRES_BACKUP_SHA256:-$BACKUP_ROOT/postgres/latest.sha256}"
CONFIG_BACKUP="${CONFIG_BACKUP_FILE:-$BACKUP_ROOT/configs/latest.tar.gz}"
CONFIG_MANIFEST="${CONFIG_BACKUP_SHA256:-$BACKUP_ROOT/configs/latest.sha256}"

for path in "$POSTGRES_BACKUP" "$POSTGRES_MANIFEST" "$CONFIG_BACKUP" "$CONFIG_MANIFEST"; do
  if [[ ! -e "$path" ]]; then
    echo "backup verification failed: missing $path" >&2
    exit 2
  fi
done

(cd "$(dirname "$POSTGRES_BACKUP")" && sha256sum -c "$(basename "$POSTGRES_MANIFEST")" >/dev/null)
(cd "$(dirname "$CONFIG_BACKUP")" && sha256sum -c "$(basename "$CONFIG_MANIFEST")" >/dev/null)
pg_restore --list "$POSTGRES_BACKUP" >/dev/null
tar -tzf "$CONFIG_BACKUP" >/dev/null
echo "{\"component\":\"backup_verification\",\"status\":\"ok\",\"postgres\":\"$POSTGRES_BACKUP\",\"configs\":\"$CONFIG_BACKUP\"}"
