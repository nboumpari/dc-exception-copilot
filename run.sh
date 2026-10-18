#!/usr/bin/env bash
# Start the API and the Streamlit UI together. Ctrl+C stops both.
#   ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

API_PORT=8000
UI_PORT=8501

for port in "$API_PORT" "$UI_PORT"; do
  if (echo > "/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
    echo "Port $port is already in use - is the app already running in another window?"
    exit 1
  fi
done

echo "Starting the API on http://localhost:$API_PORT ..."
uv run uvicorn copilot.api.app:app --port "$API_PORT" &
API_PID=$!
trap 'echo; echo "Stopping..."; kill "$API_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 60); do  # wait up to 60 s for the API to answer
  if curl -s "http://localhost:$API_PORT/health" > /dev/null; then break; fi
  if ! kill -0 "$API_PID" 2>/dev/null; then echo "The API failed to start - see the error above."; exit 1; fi
  sleep 1
done

echo
echo "  Chat UI:   http://localhost:$UI_PORT"
echo "  API docs:  http://localhost:$API_PORT/docs"
echo "  Press Ctrl+C to stop both."
echo
uv run --group ui streamlit run src/copilot/ui/streamlit_app.py --server.port "$UI_PORT"
