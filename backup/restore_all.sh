#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${RESTORE_CONFIRM:?Set RESTORE_CONFIRM=YES to restore all components}"
"$SCRIPT_DIR/restore_postgres.sh"
"$SCRIPT_DIR/restore_configs.sh"
echo "{\"component\":\"restore_all\",\"status\":\"ok\"}"
