#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="${CONFIG_SOURCE_DIR:-/opt/forex-ai-control-tower}"
BACKUP_DIR="${BACKUP_DIR:-./backups/configs}"
mkdir -p "$BACKUP_DIR"
tar --exclude='*.env' --exclude='secrets' --exclude='*.key' --exclude='*.pem' -czf "$BACKUP_DIR/configs_$(date +%Y%m%d%H%M%S).tar.gz" "$SOURCE_DIR"
