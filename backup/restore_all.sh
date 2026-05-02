#!/usr/bin/env bash
set -euo pipefail
./restore_postgres.sh
./restore_configs.sh
