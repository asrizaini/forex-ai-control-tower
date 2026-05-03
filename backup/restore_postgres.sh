#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${RESTORE_CONFIRM:?Set RESTORE_CONFIRM=YES to restore PostgreSQL}"
if [[ "$RESTORE_CONFIRM" != "YES" ]]; then
  echo "restore refused: RESTORE_CONFIRM must equal YES" >&2
  exit 2
fi

: "${POSTGRES_HOST:=127.0.0.1}"
: "${POSTGRES_DB:=forex_ai}"
: "${POSTGRES_USER:=forex_ai}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_RESTORE_FILE:?POSTGRES_RESTORE_FILE is required}"

if [[ ! -f "$POSTGRES_RESTORE_FILE" ]]; then
  echo "restore refused: PostgreSQL restore file not found" >&2
  exit 2
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
pg_restore -h "$POSTGRES_HOST" -U "$POSTGRES_USER" --dbname "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges "$POSTGRES_RESTORE_FILE"
echo "{\"component\":\"postgres_restore\",\"status\":\"ok\",\"file\":\"$POSTGRES_RESTORE_FILE\"}"
