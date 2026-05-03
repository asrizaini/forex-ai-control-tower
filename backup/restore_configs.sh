#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${RESTORE_CONFIRM:?Set RESTORE_CONFIRM=YES to restore configs}"
if [[ "$RESTORE_CONFIRM" != "YES" ]]; then
  echo "restore refused: RESTORE_CONFIRM must equal YES" >&2
  exit 2
fi

: "${CONFIG_RESTORE_FILE:?CONFIG_RESTORE_FILE is required}"
TARGET_DIR="${CONFIG_TARGET_DIR:-/opt/forex-ai-control-tower}"

if [[ ! -f "$CONFIG_RESTORE_FILE" ]]; then
  echo "restore refused: config restore file not found" >&2
  exit 2
fi

tar -xzf "$CONFIG_RESTORE_FILE" -C "$TARGET_DIR"
echo "{\"component\":\"configs_restore\",\"status\":\"ok\",\"file\":\"$CONFIG_RESTORE_FILE\"}"
