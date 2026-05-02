#!/usr/bin/env bash
set -euo pipefail
: "${CONFIG_RESTORE_FILE:?CONFIG_RESTORE_FILE is required}"
TARGET_DIR="${CONFIG_TARGET_DIR:-/opt/forex-ai-control-tower}"
tar -xzf "$CONFIG_RESTORE_FILE" -C "$TARGET_DIR"
