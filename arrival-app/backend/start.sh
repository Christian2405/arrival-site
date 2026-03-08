#!/bin/bash
# Arrival Backend — starts FastAPI + LiveKit Agent

echo "[start.sh] ========================================="
echo "[start.sh] Arrival Backend Starting"
echo "[start.sh] ========================================="
echo "[start.sh] Python: $(python --version 2>&1)"
echo "[start.sh] LIVEKIT_URL: ${LIVEKIT_URL:-(NOT SET)}"

AGENT_LOG="/tmp/agent_output.log"

if [ -n "$LIVEKIT_URL" ] && [ -n "$LIVEKIT_API_KEY" ] && [ -n "$LIVEKIT_API_SECRET" ]; then
    echo "[start.sh] Starting LiveKit agent (output → $AGENT_LOG)..."
    python -m livekit_agent.agent start \
        --url "${LIVEKIT_URL}" \
        --api-key "${LIVEKIT_API_KEY}" \
        --api-secret "${LIVEKIT_API_SECRET}" \
        --log-level INFO > "$AGENT_LOG" 2>&1 &
    AGENT_PID=$!
    echo "[start.sh] Agent PID: $AGENT_PID"

    sleep 8
    if kill -0 $AGENT_PID 2>/dev/null; then
        echo "[start.sh] ✓ Agent alive after 8s"
        echo "[start.sh] Agent output so far:"
        tail -20 "$AGENT_LOG"
    else
        wait $AGENT_PID 2>/dev/null
        echo "[start.sh] ✗ Agent crashed (exit $?)"
        echo "[start.sh] Agent output:"
        cat "$AGENT_LOG"
    fi
else
    echo "[start.sh] ✗ LiveKit env vars not set"
fi

echo "[start.sh] Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
