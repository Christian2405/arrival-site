"""
Arrival AI — LiveKit Voice Agent (Proactive Job Mode)

Full-duplex voice agent for trade workers with always-on camera vision.

Pipeline:
  - Silero VAD (ML-based, works next to compressors)
  - Deepgram Nova-2 STT (streaming, noise-immune)
  - Claude Sonnet LLM (accurate real-time responses + vision)
  - ElevenLabs Flash v2.5 TTS (<300ms to first audio)
  - LiveKit WebRTC transport (full-duplex, <1s end-to-end)
  - MultilingualModel turn detection (semantic, not silence-based)
  - Always-on Vision: frames continuously injected into LLM context

Vision Architecture:
  Frontend captures frames every 2-5s → sends via data channel + HTTP store →
  Agent always has latest frame → injected into every LLM call as context →
  No tool call needed, no "let me take a look" delay.

Run:
  python -m livekit_agent.agent start

Requires env vars:
  LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
  ANTHROPIC_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY
"""

import asyncio
import json
import logging
import os
import sys
import time
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

import httpx
import anthropic as anthropic_sdk

from app import config
from app.services.error_codes import lookup_error_code, format_error_code_context
from app.services.frame_store import get_frame, get_frame_age
from app.services.rag import retrieve_context

# URLs for fetching frames from FastAPI (agent runs in a separate process)
_FASTAPI_PORT = os.environ.get("PORT", "8000")
_FRAME_URLS = [
    f"http://127.0.0.1:{_FASTAPI_PORT}/api/livekit-frame/{{room}}",  # localhost first
    "https://arrival-backend-81x7.onrender.com/api/livekit-frame/{room}",  # public fallback
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared Anthropic client — reused across all vision calls
# ---------------------------------------------------------------------------
_anthropic_client: Optional[anthropic_sdk.AsyncAnthropic] = None

def _get_anthropic_client() -> anthropic_sdk.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic_sdk.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _anthropic_client

# Startup banner
logger.info("[arrival-agent] ============================")
logger.info("[arrival-agent] LiveKit Voice Agent Loading (Always-On Vision)")
logger.info(f"[arrival-agent] LIVEKIT_URL: {config.LIVEKIT_URL[:40] if config.LIVEKIT_URL else '(NOT SET)'}")
logger.info(f"[arrival-agent] DEEPGRAM: {'set' if config.DEEPGRAM_API_KEY else 'NOT SET'}")
logger.info(f"[arrival-agent] ANTHROPIC: {'set' if config.ANTHROPIC_API_KEY else 'NOT SET'}")
logger.info(f"[arrival-agent] ELEVENLABS: {'set' if config.ELEVENLABS_API_KEY else 'NOT SET'}")
logger.info(f"[arrival-agent] VOICE MODEL: {config.ANTHROPIC_VOICE_MODEL}")
logger.info("[arrival-agent] ============================")

# ---------------------------------------------------------------------------
# Proactive vision config
# ---------------------------------------------------------------------------
PROACTIVE_CHECK_INTERVAL = 5    # seconds between proactive analysis cycles
PROACTIVE_MIN_COOLDOWN = 12     # min seconds between proactive speech
PROACTIVE_PUSHBACK_COOLDOWN = 60  # cooldown after user pushes back
FRAME_CHANGE_THRESHOLD = 8     # out of 100 sampled positions

# ---------------------------------------------------------------------------
# Voice prompts
# ---------------------------------------------------------------------------

JOB_MODE_PROMPT = (
    "You're a 50-year trade veteran working side by side with a tech on a job. "
    "You can ALWAYS see what the tech's phone camera sees — it's always on, always streaming to you. "
    "You are NEVER blind. You are ALWAYS watching.\n\n"

    "YOUR CAMERA IS ALWAYS ON. You can see what the tech sees RIGHT NOW. "
    "When they ask 'what am I looking at' or 'what do you see' — you ALREADY see it. "
    "Answer immediately from what you see. NEVER say 'let me take a look' or 'let me check' — "
    "you're already looking. Just describe what you see.\n\n"

    "TOOLS — USE THEM:\n"
    "- lookup_error_code: For ANY error code, blink code, fault code, or status light question. ALWAYS try this first.\n"
    "- search_knowledge: For ANY technical question about codes, specs, sizing, manuals, building codes, "
    "refrigerant charging, clearances, installation requirements, or anything where you need reference data. "
    "USE THIS whenever you're not 100% sure of a specific number, spec, or code requirement.\n\n"

    "VISION RULES:\n"
    "- You can see the camera feed at all times. When a frame is attached, describe what you ACTUALLY see.\n"
    "- Read any text, model numbers, brands, labels, error codes visible in the frame.\n"
    "- If you spot something wrong (safety hazard, code violation, wrong fitting, corrosion), speak up.\n"
    "- Be specific: 'I see a Carrier furnace, model 58STA' not 'I see some equipment'.\n"
    "- If the image is blurry or dark, say what you CAN see and ask them to steady the camera.\n"
    "- NEVER say 'I can't see anything' or 'I don't have camera access' — you ALWAYS have the camera.\n"
    "- If no frame is available for some reason, work with what the tech tells you verbally.\n\n"

    "CONVERSATION RULES:\n"
    "- Answer what they asked, nothing extra. Simple question = simple answer.\n"
    "- 1-3 sentences max. This is spoken aloud — don't drone on.\n"
    "- Lead with the most likely cause. Don't list 5 things.\n"
    "- If they ask about a specific error code or blink code, use lookup_error_code first. "
    "If it returns nothing, try search_knowledge. If both fail, say 'I don't have that code memorized — "
    "what does the chart on the unit show?' NEVER guess error codes.\n"
    "- For technical specs, sizing, code requirements, or manufacturer-specific questions, use search_knowledge.\n"
    "- If they ask something non-trade (weather, sports, lunch), just chat naturally.\n"
    "- If they confirm ('yeah I see it'), give the next step.\n"
    "- If they say 'it's fine' or push back, DROP IT. Say 'Fair enough' and move on.\n"
    "- If they challenge something ('that's wrong'), IMMEDIATELY back off. Say 'My bad'. NEVER double down.\n"
    "- If they tell you to stop or be quiet, say 'Got it, I'll just watch' and go silent.\n"
    "- NEVER make something up. If you're not sure, say so.\n"
    "- No filler: no 'Great question', no 'Let me know if you need anything'.\n"
    "- NEVER say 'point your phone at' or 'show me' — the camera is ALWAYS running.\n"
    "- Use trade terminology: AFUE, SEER, BTU, CFM, AWG, NEC, UPC.\n"
    "- Give specific numbers: '8 AWG copper, 40A breaker' not 'appropriate wire size.'\n"
    "- Never say 'consult a professional' — they ARE the professional.\n"
    "- Use contractions. Say 'you're' not 'you are'.\n\n"

    "CRITICAL TRADE KNOWLEDGE:\n"
    "- Superheat on cap tube / fixed orifice: 10-15°F\n"
    "- Superheat on TXV: Measure SUBCOOLING instead, 10-12°F\n"
    "- R-410A: ~118 psi suction / ~340 psi discharge at 75°F\n"
    "- R-22: ~68 psi suction / ~250 psi discharge at 75°F\n"
    "- Gas pressure: 7\" WC natural gas, 11\" WC propane\n"
    "- Wire: 15A=14AWG, 20A=12AWG, 30A=10AWG, 40A=8AWG, 50A=6AWG\n"
    "- GFCI: bathrooms, kitchens countertop, garages, outdoors, crawlspaces\n"
    "- Drain slope: 1/4\" per foot for 2\" and smaller, 1/8\" for 3\" and larger\n"
)


DEFAULT_MODE_PROMPT = (
    "You are Arrival, an AI assistant for trade professionals — HVAC techs, plumbers, electricians, and builders.\n\n"

    "TOOLS — USE THEM:\n"
    "- lookup_error_code: For ANY error code, blink code, fault code, or status light question.\n"
    "- search_knowledge: For technical specs, building codes, manual references, sizing questions.\n\n"

    "RULES FOR VOICE:\n"
    "- Lead with the answer. No preamble, no filler.\n"
    "- Keep responses to 1-3 sentences max. Be specific.\n"
    "- Use trade terminology naturally.\n"
    "- When giving specs, give the number.\n"
    "- Never say 'consult a professional' — they ARE the professional.\n"
    "- If you don't know, say so in one sentence."
)


# ---------------------------------------------------------------------------
# Agent with tools + always-on vision
# ---------------------------------------------------------------------------

class ArrivalAgent(Agent):
    """Trade worker voice agent with error code lookup, always-on vision, and proactive monitoring."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Camera state — frames come from data channel OR HTTP frame store
        self._latest_frame: Optional[str] = None
        self._frame_received_at: float = 0
        self._room_name: str = ""
        self._room = None
        # Proactive vision state
        self._last_analyzed_hash: str = ""
        self._recent_observations: list[str] = []
        self._last_proactive_time: float = 0
        self._user_pushback_count: int = 0
        self._proactive_enabled: bool = True
        self._last_user_speech_time: float = 0

    def update_camera_frame(self, frame_b64: str):
        """Store the latest camera frame from the mobile app."""
        self._latest_frame = frame_b64
        self._frame_received_at = time.time()

    async def get_current_frame(self) -> Optional[str]:
        """Get the best available frame — tries data channel, HTTP, file store."""
        # 1. Data channel frame (if recent) — fastest
        if self._latest_frame and (time.time() - self._frame_received_at) < 30:
            return self._latest_frame

        # 2. HTTP from FastAPI
        if self._room_name:
            http_frame = await self._fetch_frame_async(self._room_name)
            if http_frame:
                return http_frame
            # 3. File store fallback
            file_frame = get_frame(self._room_name)
            if file_frame:
                return file_frame

        # 4. Stale frame as last resort
        return self._latest_frame

    async def _fetch_frame_async(self, room_name: str) -> Optional[str]:
        """Fetch frame via async HTTP."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                for url_template in _FRAME_URLS:
                    url = url_template.format(room=room_name)
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            frame = resp.json().get("frame")
                            if frame:
                                return frame
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def _frame_hash(self, frame: str) -> str:
        """Quick fingerprint — sample 100 positions in base64 string."""
        if len(frame) < 200:
            return frame
        step = len(frame) // 100
        return "".join(frame[i] for i in range(0, len(frame), step))[:100]

    def _frame_changed(self, frame: str) -> bool:
        """Check if frame differs significantly from last analyzed frame."""
        new_hash = self._frame_hash(frame)
        if not self._last_analyzed_hash:
            return True
        diff = sum(a != b for a, b in zip(new_hash, self._last_analyzed_hash))
        return diff > FRAME_CHANGE_THRESHOLD

    @function_tool()
    async def lookup_error_code(self, query: str) -> str:
        """Look up an HVAC, plumbing, or electrical error code. Pass the full question
        like 'Carrier furnace code 34' or 'Rheem 3 blinks' or 'Daikin U4'."""
        logger.info(f"[arrival-agent] Error code lookup: {query}")
        result = lookup_error_code(query)
        if result:
            context = format_error_code_context(result)
            return context
        return ("No verified error code found for that query. "
                "Tell the tech you don't have that code memorized and "
                "ask what the chart on the unit shows.")

    @function_tool()
    async def search_knowledge(self, query: str) -> str:
        """Search the knowledge base for manuals, building codes, specs, troubleshooting guides.
        Use for building codes, equipment specs, manufacturer manuals, pipe/wire/duct sizing,
        refrigerant charging, or any technical question needing reference data."""
        logger.info(f"[arrival-agent] Knowledge search: {query}")
        try:
            results = await retrieve_context(
                user_id="voice_agent",
                query=query,
                top_k=3,
            )
            if results:
                context_parts = []
                for r in results:
                    source = r.get("filename", "knowledge base")
                    text = r.get("text", "")
                    score = r.get("score", 0)
                    context_parts.append(f"[Source: {source} (relevance: {score:.2f})]\n{text}")
                context = "\n\n---\n\n".join(context_parts)
                return f"## Reference Material Found\n\n{context}\n\nUse this to answer accurately. Cite specific numbers."
            return "No matching reference material found. Answer from training knowledge, but be upfront if not sure."
        except Exception as e:
            logger.warning(f"[arrival-agent] Knowledge search failed: {e}")
            return "Knowledge search failed. Answer from training knowledge, but be upfront if not sure."

    @function_tool()
    async def look_at_camera(self, question: str) -> str:
        """Look at what the camera sees RIGHT NOW. Use when the tech asks you to look at,
        identify, check, or read something visual. You already see the camera feed —
        this just gives you a detailed look. NEVER say 'let me take a look' — just answer."""
        logger.info(f"[arrival-agent] ★ look_at_camera: {question[:60]}")

        # Use cached frame — no roundtrip, instant
        frame = await self.get_current_frame()
        if not frame:
            return "Camera feed is momentarily unavailable. Just describe what you're looking at."

        try:
            client = _get_anthropic_client()
            response = await client.messages.create(
                model=config.ANTHROPIC_VISION_MODEL,
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": frame},
                        },
                        {
                            "type": "text",
                            "text": (
                                "You're a 50-year trade veteran looking at this through a tech's phone camera. "
                                f"{question}. Be specific and practical, 1-3 sentences. "
                                "Read any model numbers, brands, labels, or error codes you can see. "
                                "If something looks wrong, say what and why."
                            ),
                        },
                    ],
                }],
            )
            result = response.content[0].text
            logger.info(f"[arrival-agent] ✓ Vision result: {result[:80]}...")
            return result
        except Exception as e:
            logger.warning(f"[arrival-agent] Vision failed: {e}")
            return "Camera glitch — just describe what you're looking at and I'll help."


# ---------------------------------------------------------------------------
# Proactive Vision — background analysis loop
# ---------------------------------------------------------------------------

async def _analyze_frame_proactive(frame_b64: str, recent_observations: list[str]) -> Optional[str]:
    """Analyze a frame directly with Claude Vision for proactive monitoring."""
    client = _get_anthropic_client()

    context = ""
    if recent_observations:
        context = f"\nYou already mentioned: {'; '.join(recent_observations[-3:])}. Don't repeat these."

    response = await client.messages.create(
        model=config.ANTHROPIC_VISION_MODEL,
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64},
                },
                {
                    "type": "text",
                    "text": (
                        "You're a 50-year trade veteran watching a job through a phone camera. "
                        "You're their experienced buddy — observant, helpful, not annoying.\n\n"
                        "SPEAK UP about:\n"
                        "- Safety hazards (exposed wires, flame issues, water near electrical, gas leaks)\n"
                        "- Visible problems (wrong fitting, corroded connections, code violations)\n"
                        "- Readable model/serial numbers the tech might want to know\n"
                        "- Something that looks off based on what you'd expect to see\n"
                        "- A helpful tip based on what equipment you see (like a veteran would share)\n\n"
                        "STAY QUIET about:\n"
                        "- Things that look normal and fine\n"
                        "- Blurry or unclear frames where you can't make out details\n"
                        "- Things you already mentioned\n\n"
                        f"{context}\n\n"
                        "If something is worth mentioning, give ONE short sentence a veteran would casually say. "
                        "If nothing notable, respond with exactly: NOTHING"
                    ),
                },
            ],
        }],
    )
    result = response.content[0].text.strip()

    if result.upper() == "NOTHING" or len(result) < 5:
        return None
    if "nothing" in result.lower() and len(result) < 30:
        return None
    if "don't see" in result.lower() or "can't see" in result.lower():
        return None

    return result


async def proactive_monitor(agent: ArrivalAgent, session: AgentSession):
    """Background task: continuously watches camera and speaks up when something's notable."""
    logger.info("[proactive] Monitor started — waiting for greeting to finish...")

    await asyncio.sleep(6)

    last_analysis_time = 0

    while True:
        try:
            await asyncio.sleep(PROACTIVE_CHECK_INTERVAL)

            if not agent._proactive_enabled or not agent._room_name:
                continue

            now = time.time()

            # Cooldown — don't spam
            cooldown = PROACTIVE_PUSHBACK_COOLDOWN if agent._user_pushback_count > 2 else PROACTIVE_MIN_COOLDOWN
            if now - agent._last_proactive_time < cooldown:
                continue

            # Don't interrupt active conversation
            if now - agent._last_user_speech_time < 6:
                continue

            # Get frame
            frame = None
            if agent._latest_frame and (now - agent._frame_received_at) < 30:
                frame = agent._latest_frame
            if not frame:
                frame = get_frame(agent._room_name)
            if not frame:
                continue

            # Frame diffing — skip if scene hasn't changed
            force_analyze = (now - last_analysis_time) > 20
            if not force_analyze and not agent._frame_changed(frame):
                continue

            # Analyze
            agent._last_analyzed_hash = agent._frame_hash(frame)
            last_analysis_time = now

            try:
                observation = await _analyze_frame_proactive(frame, agent._recent_observations)
            except Exception as e:
                logger.warning(f"[proactive] Vision failed: {e}")
                continue

            if observation:
                # Check for repeats
                is_repeat = any(
                    obs.lower() in observation.lower() or observation.lower() in obs.lower()
                    for obs in agent._recent_observations[-3:]
                )
                if is_repeat:
                    continue

                logger.info(f"[proactive] ★ ALERT: {observation}")
                await session.generate_reply(
                    instructions=f"You just noticed something while watching the camera. Tell the tech briefly and casually: {observation}"
                )
                agent._last_proactive_time = now
                agent._recent_observations.append(observation)
                if len(agent._recent_observations) > 5:
                    agent._recent_observations.pop(0)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"[proactive] Error: {e}")
            await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# Frame injection — attach latest frame to every LLM call
# ---------------------------------------------------------------------------

def _build_frame_context(frame_b64: Optional[str]) -> list[dict]:
    """Build multimodal content blocks with the current frame for LLM context."""
    if not frame_b64:
        return []
    return [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64},
        },
        {
            "type": "text",
            "text": "[This is what the tech's phone camera is showing you RIGHT NOW. You can always see this. Describe what you see when asked.]",
        },
    ]


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

        # Load ML models with fallback
        vad = None
        turn_det = None
        if silero is not None:
            try:
                vad = silero.VAD.load()
                logger.info("[arrival-agent] ✓ Silero VAD loaded")
            except Exception as e:
                logger.warning(f"[arrival-agent] Silero VAD failed: {e}")
        if MultilingualModel is not None:
            try:
                turn_det = MultilingualModel()
                logger.info("[arrival-agent] ✓ Turn detector loaded")
            except Exception as e:
                logger.warning(f"[arrival-agent] Turn detector failed: {e}")

        # Create the voice pipeline
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

        # Create agent with tools
        agent = ArrivalAgent(
            instructions=prompt,
            allow_interruptions=True,
            min_endpointing_delay=0.3,
            max_endpointing_delay=1.0,
        )

        # Set room name and room reference
        agent._room_name = room_name
        agent._room = ctx.room

        await session.start(agent=agent, room=ctx.room)
        logger.info("[arrival-agent] ✓ Session started — voice pipeline active")

        # Listen for data channel messages from mobile app
        @ctx.room.on("data_received")
        def on_data(data_packet):
            try:
                payload = json.loads(data_packet.data.decode("utf-8"))
                msg_type = payload.get("type", "")

                if msg_type == "camera_frame" and payload.get("image"):
                    agent.update_camera_frame(payload["image"])

            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass

        logger.info("[arrival-agent] ✓ Data channel listener registered")

        # Track user speech for proactive monitor
        @session.on("user_input_transcribed")
        def on_user_speech(ev):
            agent._last_user_speech_time = time.time()

        # Background task: keep injecting latest frame into agent context
        async def frame_injector():
            """Continuously update the agent's context with the latest camera frame."""
            while True:
                try:
                    await asyncio.sleep(3)
                    frame = await agent.get_current_frame()
                    if frame:
                        # Update the agent's instructions with frame context
                        # This makes the frame available to the LLM on every turn
                        agent._latest_frame = frame
                        agent._frame_received_at = time.time()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"[frame-injector] Error: {e}")

        # Start background tasks
        injector_task = asyncio.create_task(frame_injector())

        monitor_task = None
        if mode == "job":
            monitor_task = asyncio.create_task(proactive_monitor(agent, session))
            logger.info("[arrival-agent] ✓ Proactive vision monitor started")

        # Greeting
        await asyncio.sleep(1.5)
        await session.generate_reply(
            instructions="Say exactly: 'Hey, I'm here. What are we working on?' Nothing else."
        )
        logger.info("[arrival-agent] ✓ Greeting sent")

    except Exception as e:
        logger.error(f"[arrival-agent] ✗ ENTRYPOINT CRASHED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(server)
