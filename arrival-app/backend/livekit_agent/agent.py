"""
Arrival AI — LiveKit Voice Agent

Full-duplex voice agent for trade workers.

Pipeline:
  - Deepgram Nova-2 STT (server-side VAD, works next to compressors)
  - Claude Haiku LLM (fast real-time responses)
  - ElevenLabs Flash v2.5 TTS (<300ms to first audio)
  - LiveKit WebRTC transport (full-duplex, <1s end-to-end)
  - MultilingualModel turn detection (semantic, not silence-based)

Run:
  python -m livekit_agent.agent start

Requires env vars:
  LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
  ANTHROPIC_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add backend root to path so we can import from app.services
_backend_root = os.path.join(os.path.dirname(__file__), "..")
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

# CRITICAL: LiveKit agents framework spawns worker subprocesses that don't
# inherit the parent's dotenv. Load .env explicitly here so every subprocess
# gets the API keys (Deepgram, Anthropic, ElevenLabs).
from dotenv import load_dotenv
_env_file = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_file, override=True)

from livekit.agents import (
    Agent,
    AgentSession,
    AgentServer,
    JobContext,
    cli,
)
from livekit.plugins import deepgram, anthropic, elevenlabs, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from app import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice prompt — short, direct, optimized for spoken responses
# ---------------------------------------------------------------------------

VOICE_PROMPT = """You are Arrival, an AI field assistant for trade professionals — HVAC techs, plumbers, electricians, and builders.

RULES FOR VOICE:
- Lead with the answer. No preamble, no filler.
- Keep responses to 2-3 sentences max. Be specific.
- Use trade terminology naturally — AFUE, SEER, BTU, CFM, AWG, NEC, UPC.
- When giving specs, give the number. "8 AWG copper, 40A breaker" not "appropriate wire size."
- Never say "consult a professional" — they ARE the professional.
- If you don't know, say so in one sentence. Don't ramble.
- You're talking to someone on a job site. Respect their time."""


# ---------------------------------------------------------------------------
# Agent Server & Entrypoint
# ---------------------------------------------------------------------------

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Called when a participant joins a LiveKit room that needs an agent."""
    await ctx.connect()

    # Parse metadata for user info
    room_name = ctx.room.name or ""
    mode = "job"
    user_id = "unknown"

    for participant in ctx.room.remote_participants.values():
        if participant.metadata:
            try:
                meta = json.loads(participant.metadata)
                user_id = meta.get("user_id", user_id)
                mode = meta.get("mode", mode)
            except (json.JSONDecodeError, TypeError):
                pass
            break

    logger.info(f"[arrival-agent] Room={room_name} user={user_id} mode={mode}")

    # Create the voice pipeline — optimized for speed
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-2",
            language="en",
            api_key=config.DEEPGRAM_API_KEY,
        ),
        llm=anthropic.LLM(
            model=config.ANTHROPIC_VOICE_MODEL,
            api_key=config.ANTHROPIC_API_KEY,
        ),
        tts=elevenlabs.TTS(
            voice_id=config.ELEVENLABS_JOB_VOICE_ID,
            model="eleven_flash_v2_5",
            api_key=config.ELEVENLABS_API_KEY,
        ),
        turn_detection=MultilingualModel(),
    )

    # Create agent — no tools for now, pure speed
    agent = Agent(
        instructions=VOICE_PROMPT,
        allow_interruptions=True,
        min_endpointing_delay=0.5,
        max_endpointing_delay=1.5,
    )

    await session.start(agent=agent, room=ctx.room)

    # In default/voice mode, greet. In job mode, stay silent until they talk.
    if mode == "default":
        await session.generate_reply(
            instructions="Say a very brief greeting, like 'Hey, what's up?' — 5 words max."
        )
    # Job mode: agent is silently monitoring. Tech speaks when ready.


if __name__ == "__main__":
    cli.run_app(server)
