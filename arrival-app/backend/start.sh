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

# Quick import check — only verify SDK is installed (don't load full agent which loads ML models)
echo "[start.sh] Checking SDK imports..."
if python -c "
from livekit.agents import Agent, AgentSession, AgentServer
from livekit.plugins import deepgram, anthropic, elevenlabs
print('[start.sh] SDK imports OK')
" 2>&1; then
    echo "[start.sh] ✓ SDK OK — starting LiveKit agent"
    # Start agent in background — it loads ML models (Silero, etc) on startup which takes time
    python -m livekit_agent.agent start \
        --url "${LIVEKIT_URL}" \
        --api-key "${LIVEKIT_API_KEY}" \
        --api-secret "${LIVEKIT_API_SECRET}" \
        --log-level INFO 2>&1 &
    AGENT_PID=$!
    echo "[start.sh] LiveKit agent PID: $AGENT_PID (loading models in background...)"

    # Give it more time — ML model loading is slow on 0.5 CPU
    sleep 8
    if kill -0 $AGENT_PID 2>/dev/null; then
        echo "[start.sh] ✓ LiveKit agent still running after 8s"
    else
        wait $AGENT_PID 2>/dev/null
        AGENT_EXIT=$?
        echo "[start.sh] ✗ LiveKit agent CRASHED on startup (exit code: $AGENT_EXIT)"
        echo "[start.sh] FastAPI will continue without voice agent"
    fi
else
    echo "[start.sh] ✗ SDK import check failed — skipping LiveKit agent"
fi

# Start FastAPI in foreground — Render monitors this process
echo "[start.sh] Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
