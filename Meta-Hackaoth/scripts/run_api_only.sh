#!/usr/bin/env bash
set -euo pipefail
# Local / simple container: API only on ${PORT:-8000}
LISTEN_PORT="${PORT:-8000}"
exec uvicorn server.app:app --host 0.0.0.0 --port "${LISTEN_PORT}"
