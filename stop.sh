#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-${PORT:-8000}}"

echo "[stop.sh] Stop uvicorn/procs op poort ${PORT} (indien aanwezig)..."

# 1) Via lsof
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti :"$PORT" || true)
  if [ -n "${PIDS:-}" ]; then
    echo "[stop.sh] kill -9 ${PIDS}"
    kill -9 ${PIDS} || true
  fi
fi

# 2) Via fuser
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
fi

# 3) Vangnet: pkill op uvicorn-regel
pkill -f "uvicorn .*:${PORT}" >/dev/null 2>&1 || true
pkill -f "python -m uvicorn .*:${PORT}" >/dev/null 2>&1 || true

echo "[stop.sh] Klaar. (OK als er niets te stoppen was)"
