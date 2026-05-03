#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/forex-ai-control-tower/backups}"
MANIFEST_DIR="$BACKUP_ROOT/manifests"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
MANIFEST_FILE="$MANIFEST_DIR/backup_${TIMESTAMP}.jsonl"

mkdir -p "$MANIFEST_DIR"
"$SCRIPT_DIR/backup_postgres.sh" | tee -a "$MANIFEST_FILE"
"$SCRIPT_DIR/backup_configs.sh" | tee -a "$MANIFEST_FILE"
sha256sum "$MANIFEST_FILE" > "$MANIFEST_FILE.sha256"
ln -sfn "$(basename "$MANIFEST_FILE")" "$MANIFEST_DIR/latest.jsonl"
ln -sfn "$(basename "$MANIFEST_FILE.sha256")" "$MANIFEST_DIR/latest.sha256"
echo "{\"component\":\"backup_all\",\"status\":\"ok\",\"manifest\":\"$MANIFEST_FILE\"}"
