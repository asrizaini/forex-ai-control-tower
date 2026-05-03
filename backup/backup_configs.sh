#!/usr/bin/env bash
set -euo pipefail
umask 077
SOURCE_DIR="${CONFIG_SOURCE_DIR:-/opt/forex-ai-control-tower}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/forex-ai-control-tower/backups}"
BACKUP_DIR="${CONFIG_BACKUP_DIR:-$BACKUP_ROOT/configs}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="$BACKUP_DIR/configs_${TIMESTAMP}.tar.gz"
MANIFEST_FILE="$BACKUP_DIR/configs_${TIMESTAMP}.sha256"

mkdir -p "$BACKUP_DIR"
tar \
  --exclude='*.env' \
  --exclude='*.key' \
  --exclude='*.pem' \
  --exclude='*.token' \
  --exclude='*.log' \
  --exclude='secrets' \
  --exclude='backups' \
  --exclude='postgres_data' \
  --exclude='grafana_data' \
  -czf "$OUTPUT_FILE" "$SOURCE_DIR/app" "$SOURCE_DIR/monitoring" "$SOURCE_DIR/control-stack.compose.yml"
sha256sum "$OUTPUT_FILE" > "$MANIFEST_FILE"
ln -sfn "$(basename "$OUTPUT_FILE")" "$BACKUP_DIR/latest.tar.gz"
ln -sfn "$(basename "$MANIFEST_FILE")" "$BACKUP_DIR/latest.sha256"
echo "{\"component\":\"configs\",\"status\":\"ok\",\"file\":\"$OUTPUT_FILE\",\"manifest\":\"$MANIFEST_FILE\"}"
