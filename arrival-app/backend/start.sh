#!/bin/bash
# Arrival Backend — starts both FastAPI and LiveKit Agent
# FastAPI handles REST/WebSocket endpoints
# LiveKit Agent handles full-duplex voice via WebRTC

set -e

echo "[start.sh] Starting LiveKit voice agent in background..."
python -m livekit_agent.agent start &
AGENT_PID=$!
echo "[start.sh] LiveKit agent PID: $AGENT_PID"

echo "[start.sh] Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
API_PID=$!
echo "[start.sh] FastAPI PID: $API_PID"

# Wait for either process to exit, then kill the other
wait -n $AGENT_PID $API_PID
EXIT_CODE=$?
echo "[start.sh] A process exited with code $EXIT_CODE — shutting down..."

kill $AGENT_PID 2>/dev/null || true
kill $API_PID 2>/dev/null || true
wait

exit $EXIT_CODE
