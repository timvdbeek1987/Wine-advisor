#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-${PORT:-8000}}"
HOST="${HOST:-0.0.0.0}"

echo "[start.sh] App starten op ${HOST}:${PORT}..."

# Activeer venv indien aanwezig
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  echo "[start.sh] .venv geactiveerd."
else
  echo "[start.sh] Let op: geen .venv gevonden. Ik probeer toch te starten."
fi

# Kies uvicorn commando
if command -v uvicorn >/dev/null 2>&1; then
  CMD="uvicorn app:app --host ${HOST} --port ${PORT} --reload"
else
  echo "[start.sh] 'uvicorn' niet gevonden in PATH, probeer 'python -m uvicorn'..."
  CMD="python -m uvicorn app:app --host ${HOST} --port ${PORT} --reload"
fi

echo "[start.sh] Command: $CMD"
exec $CMD
