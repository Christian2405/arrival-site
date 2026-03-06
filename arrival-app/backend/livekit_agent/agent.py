"""
Arrival AI — LiveKit Voice Agent

Full-duplex voice agent for trade workers.

Pipeline:
  - Silero VAD (ML-based, works next to compressors)
  - Deepgram Nova-2 STT (streaming, noise-immune)
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
from typing import Optional

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
    function_tool,
)
from livekit.plugins import deepgram, anthropic, elevenlabs

# Optional ML plugins — may fail to import if deps are missing
try:
    from livekit.plugins import silero
except ImportError:
    silero = None
    print("[arrival-agent] WARNING: Silero plugin not available")

try:
    from livekit.plugins.turn_detector.multilingual import MultilingualModel
except ImportError:
    try:
        from livekit.plugins.turn_detector import MultilingualModel
    except ImportError:
        MultilingualModel = None
        print("[arrival-agent] WARNING: MultilingualModel not available")

from app import config
from app.services.error_codes import lookup_error_code, format_error_code_context

logger = logging.getLogger(__name__)

# Startup banner — visible in Render logs for diagnostics
logger.info("[arrival-agent] ============================")
logger.info("[arrival-agent] LiveKit Voice Agent Loading")
logger.info(f"[arrival-agent] LIVEKIT_URL: {config.LIVEKIT_URL[:40] if config.LIVEKIT_URL else '(NOT SET)'}")
logger.info(f"[arrival-agent] DEEPGRAM: {'set' if config.DEEPGRAM_API_KEY else 'NOT SET'}")
logger.info(f"[arrival-agent] ANTHROPIC: {'set' if config.ANTHROPIC_API_KEY else 'NOT SET'}")
logger.info(f"[arrival-agent] ELEVENLABS: {'set' if config.ELEVENLABS_API_KEY else 'NOT SET'}")
logger.info("[arrival-agent] ============================")

# ---------------------------------------------------------------------------
# Voice prompts
# ---------------------------------------------------------------------------

JOB_MODE_PROMPT = (
    "You're a 50-year vet working alongside a tech on a job. You're their buddy — "
    "you talk about anything, answer anything. Short, confident, natural. "
    "1-3 sentences max. This is spoken aloud — don't drone on.\n\n"

    "RULES:\n"
    "- Answer what they asked, nothing extra. Simple question = simple answer.\n"
    "- Lead with the most likely cause. Don't list 5 things.\n"
    "- If they ask about a specific error code or blink code, use the lookup_error_code tool to get the EXACT data. "
    "If the tool returns nothing, say 'I don't have that code memorized — what does the chart on the unit show?' NEVER guess error codes.\n"
    "- If they ask something non-trade (weather, sports, lunch), just chat naturally. You're a person, not a manual.\n"
    "- If you tell them to check something, ask what they find.\n"
    "- If they confirm ('yeah I see it'), give the next step.\n"
    "- If they say 'it's fine' or 'no' or push back, DROP IT IMMEDIATELY. Say 'Fair enough' or 'Got it' and move on.\n"
    "- If they challenge something you said ('what are you talking about', 'there's no leak', 'that's wrong'), "
    "IMMEDIATELY back off. Say 'My bad' or 'Alright, scratch that'. NEVER double down. NEVER insist.\n"
    "- NEVER make something up. If you're not sure, say so. A wrong answer wastes the tech's time.\n"
    "- No filler: no 'Great question', no 'Let me know if you need anything'.\n"
    "- If they ask you to LOOK at something, identify something, check something visual, or read a model number, "
    "use the look_at_camera tool. Their phone camera is pointed at the job.\n"
    "- Use trade terminology naturally — AFUE, SEER, BTU, CFM, AWG, NEC, UPC.\n"
    "- When giving specs, give the number. '8 AWG copper, 40A breaker' not 'appropriate wire size.'\n"
    "- Never say 'consult a professional' — they ARE the professional.\n"
    "- Use contractions. Say 'you're' not 'you are', 'don't' not 'do not'.\n\n"

    "EXAMPLES:\n"
    "Q: 'Superheat target on a TXV?' → 'Subcooling, not superheat — 10 to 12 degrees. What are you reading?'\n"
    "Q: 'Carrier keeps short cycling' → 'Flame sensor. Pull it, emery cloth, fixes it 80% of the time.'\n"
    "Q: 'What size wire for 40 amps?' → '8 gauge copper. Over 50 feet, bump to 6.'\n"
    "Q: 'Yeah I see the corrosion' → 'Emery cloth and NoOx. Want me to walk you through it?'\n"
    "Q: 'There's no leak here' → 'My bad, must have misread that. What are you looking at?'\n"
    "Q: 'What do you think about the Bears game?' → 'Don't get me started. What a season though.'"
)


DEFAULT_MODE_PROMPT = (
    "You are Arrival, an AI assistant for trade professionals — HVAC techs, plumbers, electricians, and builders.\n\n"

    "RULES FOR VOICE:\n"
    "- Lead with the answer. No preamble, no filler.\n"
    "- Keep responses to 1-3 sentences max. Be specific.\n"
    "- Use trade terminology naturally — AFUE, SEER, BTU, CFM, AWG, NEC, UPC.\n"
    "- When giving specs, give the number. '8 AWG copper, 40A breaker' not 'appropriate wire size.'\n"
    "- Never say 'consult a professional' — they ARE the professional.\n"
    "- If they ask about a specific error code or blink code, use the lookup_error_code tool first.\n"
    "- If you don't know, say so in one sentence. Don't ramble.\n"
    "- You're talking to someone on a job site. Respect their time."
)


# ---------------------------------------------------------------------------
# Agent with error code lookup tool
# ---------------------------------------------------------------------------

class ArrivalAgent(Agent):
    """Trade worker voice agent with error code lookup and camera vision."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._latest_frame: Optional[str] = None  # base64 JPEG from phone camera

    def update_camera_frame(self, frame_b64: str):
        """Store the latest camera frame from the mobile app."""
        self._latest_frame = frame_b64

    @function_tool()
    async def lookup_error_code(self, query: str) -> str:
        """Look up an HVAC, plumbing, or electrical error code. Pass the full question
        like 'Carrier furnace code 34' or 'Rheem 3 blinks' or 'Daikin U4'."""
        logger.info(f"[arrival-agent] Error code lookup: {query}")
        result = lookup_error_code(query)
        if result:
            context = format_error_code_context(result)
            logger.info(f"[arrival-agent] Found: {result['brand']} {result['code']}")
            return context
        logger.info("[arrival-agent] No error code match found")
        return ("No verified error code found for that query. "
                "Tell the tech you don't have that code memorized and "
                "ask what the chart on the unit shows.")

    @function_tool()
    async def look_at_camera(self, question: str) -> str:
        """Look at what the user's phone camera sees. Use this when they ask you to
        look at something, identify something, check something, read a model number,
        or ask 'what do you see' / 'what am I looking at' / 'what's wrong here'."""
        if not self._latest_frame:
            return ("I can't see anything right now — the camera feed isn't available. "
                    "Ask the tech to make sure the camera is pointed at what they want you to see.")

        logger.info("[arrival-agent] Looking at camera frame...")
        try:
            import anthropic as anthropic_sdk
            client = anthropic_sdk.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model=config.ANTHROPIC_VOICE_MODEL,
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": self._latest_frame,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "You're a 50-year trade veteran looking at this through a tech's phone camera. "
                                f"{question}. Be specific and practical, 1-3 sentences. "
                                "If you can read any model numbers, brands, or error codes, mention them."
                            ),
                        },
                    ],
                }],
            )
            result_text = response.content[0].text
            logger.info(f"[arrival-agent] Camera analysis: {result_text[:80]}...")
            return result_text
        except Exception as e:
            logger.error(f"[arrival-agent] Camera analysis failed: {e}")
            return "I tried to look but something went wrong with the camera. Ask them to describe what they see."


# ---------------------------------------------------------------------------
# Agent Server & Entrypoint
# ---------------------------------------------------------------------------

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Called when a participant joins a LiveKit room that needs an agent."""
    try:
        logger.info(f"[arrival-agent] ★ Entrypoint called — room={ctx.room.name}")
        await ctx.connect()
        logger.info(f"[arrival-agent] Connected to room: {ctx.room.name}")

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

        # Select prompt based on mode
        prompt = JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT

        # Load ML models with fallback — these download on first use and may fail
        # on memory-constrained environments (Render free tier = 512MB)
        vad = None
        turn_det = None
        if silero is not None:
            try:
                vad = silero.VAD.load()
                logger.info("[arrival-agent] ✓ Silero VAD loaded")
            except Exception as e:
                logger.warning(f"[arrival-agent] Silero VAD failed: {e} — running without VAD")
        else:
            logger.info("[arrival-agent] Silero not available — skipping VAD")

        if MultilingualModel is not None:
            try:
                turn_det = MultilingualModel()
                logger.info("[arrival-agent] ✓ Turn detector loaded")
            except Exception as e:
                logger.warning(f"[arrival-agent] Turn detector failed: {e} — using default")
        else:
            logger.info("[arrival-agent] MultilingualModel not available — skipping turn detection")

        # Log API key status
        logger.info(f"[arrival-agent] DEEPGRAM key: {'set' if config.DEEPGRAM_API_KEY else 'MISSING'}")
        logger.info(f"[arrival-agent] ANTHROPIC key: {'set' if config.ANTHROPIC_API_KEY else 'MISSING'}")
        logger.info(f"[arrival-agent] ELEVENLABS key: {'set' if config.ELEVENLABS_API_KEY else 'MISSING'}")

        # Create the voice pipeline — optimized for speed
        session_kwargs = dict(
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
                voice_id=config.ELEVENLABS_JOB_VOICE_ID if mode == "job" else (config.ELEVENLABS_VOICE_ID or config.ELEVENLABS_JOB_VOICE_ID),
                model="eleven_flash_v2_5",
                api_key=config.ELEVENLABS_API_KEY,
            ),
        )
        if vad is not None:
            session_kwargs["vad"] = vad
        if turn_det is not None:
            session_kwargs["turn_detection"] = turn_det

        session = AgentSession(**session_kwargs)
        logger.info("[arrival-agent] ✓ AgentSession created")

        # Create agent with error code lookup tool
        agent = ArrivalAgent(
            instructions=prompt,
            allow_interruptions=True,
            min_endpointing_delay=0.5,
            max_endpointing_delay=1.5,
        )

        await session.start(agent=agent, room=ctx.room)
        logger.info("[arrival-agent] ✓ Session started — voice pipeline active")

        # Listen for camera frames from the mobile app via data channel
        @ctx.room.on("data_received")
        def on_data(data_packet):
            try:
                payload = json.loads(data_packet.data.decode("utf-8"))
                if payload.get("type") == "camera_frame" and payload.get("image"):
                    agent.update_camera_frame(payload["image"])
                    logger.info("[arrival-agent] Camera frame received (%d bytes)", len(payload["image"]))
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass  # Not a camera frame — ignore

        logger.info("[arrival-agent] ✓ Camera data channel listener registered")

        # Greet to confirm the full pipeline works (STT→LLM→TTS→audio)
        await session.generate_reply(
            instructions="Say exactly: 'Hey, I'm here.' Nothing else."
        )
        logger.info("[arrival-agent] ✓ Greeting sent")

    except Exception as e:
        logger.error(f"[arrival-agent] ✗ ENTRYPOINT CRASHED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(server)
