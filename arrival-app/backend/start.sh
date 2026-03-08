#!/bin/bash
# Arrival Backend — starts FastAPI + LiveKit Agent

echo "[start.sh] Starting..."
echo "[start.sh] LIVEKIT_URL: ${LIVEKIT_URL:-(NOT SET)}"

AGENT_LOG="/tmp/agent_output.log"

if [ -n "$LIVEKIT_URL" ] && [ -n "$LIVEKIT_API_KEY" ] && [ -n "$LIVEKIT_API_SECRET" ]; then
    echo "[start.sh] Launching LiveKit agent..."
    python -m livekit_agent.agent start \
        --url "${LIVEKIT_URL}" \
        --api-key "${LIVEKIT_API_KEY}" \
        --api-secret "${LIVEKIT_API_SECRET}" \
        --log-level INFO > "$AGENT_LOG" 2>&1 &
    echo "[start.sh] Agent PID: $!"
else
    echo "[start.sh] ✗ LiveKit env vars missing — no agent"
fi

echo "[start.sh] Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
