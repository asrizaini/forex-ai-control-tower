#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${POSTGRES_HOST:=127.0.0.1}"
: "${POSTGRES_DB:=forex_ai}"
: "${POSTGRES_USER:=forex_ai}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/forex-ai-control-tower/backups}"
BACKUP_DIR="${POSTGRES_BACKUP_DIR:-$BACKUP_ROOT/postgres}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.dump"
MANIFEST_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.sha256"

mkdir -p "$BACKUP_DIR"
export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" --format=custom --no-owner --no-privileges "$POSTGRES_DB" > "$OUTPUT_FILE"
sha256sum "$OUTPUT_FILE" > "$MANIFEST_FILE"
ln -sfn "$(basename "$OUTPUT_FILE")" "$BACKUP_DIR/latest.dump"
ln -sfn "$(basename "$MANIFEST_FILE")" "$BACKUP_DIR/latest.sha256"
echo "{\"component\":\"postgres\",\"status\":\"ok\",\"file\":\"$OUTPUT_FILE\",\"manifest\":\"$MANIFEST_FILE\"}"
