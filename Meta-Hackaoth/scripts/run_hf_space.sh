#!/usr/bin/env bash
set -euo pipefail

# Hugging Face Spaces expose a single public port (default 7860 via $PORT).
# We run FastAPI on 127.0.0.1:8000 and Streamlit on 0.0.0.0:$PORT so the UI works
# and Streamlit can call the API via BACKEND_BASE_URL.

export BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
LISTEN_PORT="${PORT:-7860}"

uvicorn server.app:app --host 127.0.0.1 --port 8000 &
UV_PID="${!}"

python - <<'PY'
import time
import urllib.request

deadline = time.time() + 60
while time.time() < deadline:
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
        break
    except Exception:
        time.sleep(0.4)
else:
    raise SystemExit("FastAPI failed to start on 127.0.0.1:8000")
PY

exec streamlit run streamlit_command_center.py \
  --server.port "${LISTEN_PORT}" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
