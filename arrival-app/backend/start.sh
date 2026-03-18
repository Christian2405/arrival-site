#!/bin/bash
# Arrival Backend — starts FastAPI + LiveKit Agent

AGENT_LOG="/tmp/agent_output.log"

if [ -n "$LIVEKIT_URL" ] && [ -n "$LIVEKIT_API_KEY" ] && [ -n "$LIVEKIT_API_SECRET" ]; then
    echo "[start.sh] LiveKit env vars found — starting agent..."

    # Quick test: can we import the SDK at all?
    python -u -c "
import sys
print('[agent-test] Python:', sys.version, flush=True)
print('[agent-test] Importing livekit.agents...', flush=True)
from livekit.agents import AgentServer
print('[agent-test] AgentServer imported OK', flush=True)
" 2>&1 | tee -a "$AGENT_LOG"

    echo "[start.sh] SDK test done (exit $?)"

    # Download turn detector model if not cached
    echo "[start.sh] Downloading turn detector model..."
    python -u -m livekit_agent.agent download-files 2>&1 | tee -a "$AGENT_LOG"
    echo "[start.sh] Model download done (exit $?)"

    # Start agent — pipe to both stdout AND log file so Render shows it
    echo "[start.sh] Launching agent..."
    python -u -m livekit_agent.agent start \
        --url "${LIVEKIT_URL}" \
        --api-key "${LIVEKIT_API_KEY}" \
        --api-secret "${LIVEKIT_API_SECRET}" \
        --log-level INFO 2>&1 | tee -a "$AGENT_LOG" &
    echo "[start.sh] Agent PID: $!"
else
    echo "[start.sh] LIVEKIT env vars MISSING — agent will NOT start"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
