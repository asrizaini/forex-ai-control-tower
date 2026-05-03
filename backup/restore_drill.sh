#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_USER="${POSTGRES_USER:-forex_ai}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/forex-ai-control-tower/backups}"
POSTGRES_RESTORE_FILE="${POSTGRES_RESTORE_FILE:-$BACKUP_ROOT/postgres/latest.dump}"
DRILL_DB="forex_ai_restore_drill_$(date -u +%Y%m%d%H%M%S)"
DRILL_DIR="$BACKUP_ROOT/restore_drills"
DRILL_MARKER="$DRILL_DIR/restore_drill_$(date -u +%Y%m%dT%H%M%SZ).json"

if [[ ! -f "$POSTGRES_RESTORE_FILE" ]]; then
  echo "restore drill refused: backup dump not found" >&2
  exit 2
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
createdb -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$DRILL_DB"
cleanup() {
  dropdb -h "$POSTGRES_HOST" -U "$POSTGRES_USER" --if-exists "$DRILL_DB" >/dev/null 2>&1 || true
}
trap cleanup EXIT
pg_restore -h "$POSTGRES_HOST" -U "$POSTGRES_USER" --dbname "$DRILL_DB" --no-owner --no-privileges "$POSTGRES_RESTORE_FILE"
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$DRILL_DB" -tAc "select count(*) from information_schema.tables;" >/dev/null
mkdir -p "$DRILL_DIR"
echo "{\"component\":\"restore_drill\",\"status\":\"ok\",\"database\":\"$DRILL_DB\",\"source\":\"$POSTGRES_RESTORE_FILE\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$DRILL_MARKER"
ln -sfn "$(basename "$DRILL_MARKER")" "$DRILL_DIR/latest.json"
cat "$DRILL_MARKER"
