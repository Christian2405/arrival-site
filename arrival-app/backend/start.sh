#!/bin/bash
# Arrival Backend — starts FastAPI + LiveKit Agent

AGENT_LOG="/tmp/agent_output.log"
echo "=== Agent startup $(date) ===" > "$AGENT_LOG"

if [ -n "$LIVEKIT_URL" ] && [ -n "$LIVEKIT_API_KEY" ] && [ -n "$LIVEKIT_API_SECRET" ]; then
    # Quick test: can we import the SDK at all?
    echo "Testing SDK import..." >> "$AGENT_LOG"
    python -u -c "
import sys
print('Python:', sys.version, flush=True)
print('Importing livekit.agents...', flush=True)
from livekit.agents import AgentServer
print('AgentServer imported OK', flush=True)
" >> "$AGENT_LOG" 2>&1

    echo "SDK test done (exit $?)" >> "$AGENT_LOG"

    # Start agent with unbuffered output
    echo "Launching agent..." >> "$AGENT_LOG"
    python -u -m livekit_agent.agent start \
        --url "${LIVEKIT_URL}" \
        --api-key "${LIVEKIT_API_KEY}" \
        --api-secret "${LIVEKIT_API_SECRET}" \
        --log-level INFO >> "$AGENT_LOG" 2>&1 &
    echo "Agent PID: $!" >> "$AGENT_LOG"
else
    echo "LIVEKIT env vars missing" >> "$AGENT_LOG"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
