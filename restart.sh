#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-${PORT:-8000}}"

echo "[restart.sh] Restart op poort ${PORT}..."
bash ./stop.sh "${PORT}"
# 'exec' vervangt het shell-proces door start.sh zodat logs netjes doorlopen
exec bash ./start.sh "${PORT}"
