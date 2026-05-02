#!/usr/bin/env bash
set -euo pipefail
./backup_postgres.sh
./backup_configs.sh
