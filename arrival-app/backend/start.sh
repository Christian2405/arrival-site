#!/bin/bash
# Arrival Backend — starts FastAPI + LiveKit Agent
# LiveKit agent runs in background; if it crashes, FastAPI continues
# FastAPI runs in foreground so Render monitors it directly

echo "[start.sh] ========================================="
echo "[start.sh] Arrival Backend Starting"
echo "[start.sh] ========================================="
echo "[start.sh] CWD: $(pwd)"
echo "[start.sh] Python: $(python --version 2>&1)"
echo "[start.sh] LIVEKIT_URL: ${LIVEKIT_URL:-(NOT SET)}"
echo "[start.sh] LIVEKIT_API_KEY set: $([ -n "$LIVEKIT_API_KEY" ] && echo 'YES' || echo 'NO')"
echo "[start.sh] LIVEKIT_API_SECRET set: $([ -n "$LIVEKIT_API_SECRET" ] && echo 'YES' || echo 'NO')"

# Start agent directly — no import pre-check (it was hanging on Render)
if [ -n "$LIVEKIT_URL" ] && [ -n "$LIVEKIT_API_KEY" ] && [ -n "$LIVEKIT_API_SECRET" ]; then
    echo "[start.sh] LiveKit env vars set — starting agent..."
    python -m livekit_agent.agent start \
        --url "${LIVEKIT_URL}" \
        --api-key "${LIVEKIT_API_KEY}" \
        --api-secret "${LIVEKIT_API_SECRET}" \
        --log-level INFO 2>&1 &
    AGENT_PID=$!
    echo "[start.sh] LiveKit agent PID: $AGENT_PID"

    sleep 5
    if kill -0 $AGENT_PID 2>/dev/null; then
        echo "[start.sh] ✓ LiveKit agent running"
    else
        wait $AGENT_PID 2>/dev/null
        echo "[start.sh] ✗ LiveKit agent crashed (exit $?)"
    fi
else
    echo "[start.sh] ✗ LiveKit env vars not set — skipping agent"
fi

# Start FastAPI in foreground — Render monitors this process
echo "[start.sh] Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
