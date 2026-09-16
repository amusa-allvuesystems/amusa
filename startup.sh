#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

exec uvicorn web.server:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --log-level info
