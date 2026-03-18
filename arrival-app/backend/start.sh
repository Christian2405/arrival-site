#!/bin/bash
# Arrival Backend — starts FastAPI + LiveKit Agent

AGENT_LOG="/tmp/agent_output.log"

if [ -n "$LIVEKIT_URL" ] && [ -n "$LIVEKIT_API_KEY" ] && [ -n "$LIVEKIT_API_SECRET" ]; then
    echo "[start.sh] LiveKit env vars found — starting agent..."

    # Download turn detector model if not cached
    python -u -m livekit_agent.agent download-files >> "$AGENT_LOG" 2>&1
    echo "[start.sh] Model download done (exit $?)"

    # Start agent in background — logs to file, key events to stdout via logger
    python -u -m livekit_agent.agent start \
        --url "${LIVEKIT_URL}" \
        --api-key "${LIVEKIT_API_KEY}" \
        --api-secret "${LIVEKIT_API_SECRET}" \
        --log-level INFO >> "$AGENT_LOG" 2>&1 &
    AGENT_PID=$!
    echo "[start.sh] Agent launched (PID: $AGENT_PID)"

    # Tail agent log in background so it shows in Render dashboard
    sleep 1
    tail -f "$AGENT_LOG" &
else
    echo "[start.sh] LIVEKIT env vars MISSING — agent will NOT start"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
