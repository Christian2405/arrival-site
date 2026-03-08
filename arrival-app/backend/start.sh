#!/bin/bash
# Arrival Backend — starts FastAPI + LiveKit Agent
# LiveKit agent runs in background with a watchdog to restart on crash
# FastAPI runs in foreground so Render monitors it directly

echo "[start.sh] ========================================="
echo "[start.sh] Arrival Backend Starting"
echo "[start.sh] ========================================="
echo "[start.sh] CWD: $(pwd)"
echo "[start.sh] Python: $(python --version 2>&1)"
echo "[start.sh] LIVEKIT_URL: ${LIVEKIT_URL:-(NOT SET)}"
echo "[start.sh] LIVEKIT_API_KEY set: $([ -n "$LIVEKIT_API_KEY" ] && echo 'YES' || echo 'NO')"
echo "[start.sh] LIVEKIT_API_SECRET set: $([ -n "$LIVEKIT_API_SECRET" ] && echo 'YES' || echo 'NO')"

# Verify agent module can be imported before starting it
echo "[start.sh] Checking livekit_agent imports..."
if python -c "
import sys
sys.stdout.write('[start.sh] Importing livekit_agent.agent... ')
import livekit_agent.agent
sys.stdout.write('OK\n')
sys.stdout.write('[start.sh] Importing livekit.agents... ')
from livekit.agents import Agent, AgentSession, AgentServer
sys.stdout.write('OK\n')
sys.stdout.write('[start.sh] Importing plugins... ')
from livekit.plugins import deepgram, anthropic, elevenlabs
sys.stdout.write('OK\n')
" 2>&1; then
    echo "[start.sh] ✓ All imports OK — starting LiveKit agent with watchdog"

    # Watchdog loop: restart agent if it crashes
    (
        while true; do
            python -m livekit_agent.agent start \
                --url "${LIVEKIT_URL}" \
                --api-key "${LIVEKIT_API_KEY}" \
                --api-secret "${LIVEKIT_API_SECRET}" \
                --log-level INFO 2>&1
            EXIT_CODE=$?
            echo "[start.sh] ⚠ LiveKit agent exited (code: $EXIT_CODE) — restarting in 5s..."
            sleep 5
        done
    ) &
    WATCHDOG_PID=$!
    echo "[start.sh] LiveKit agent watchdog PID: $WATCHDOG_PID"

    # Brief check — did it crash immediately?
    sleep 3
    if kill -0 $WATCHDOG_PID 2>/dev/null; then
        echo "[start.sh] ✓ LiveKit agent watchdog running"
    else
        echo "[start.sh] ✗ LiveKit agent watchdog failed to start"
        echo "[start.sh] FastAPI will continue without voice agent"
    fi
else
    echo "[start.sh] ✗ Import check failed — skipping LiveKit agent"
fi

# Start FastAPI in foreground — Render monitors this process
echo "[start.sh] Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
