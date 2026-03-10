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
FRAME_CHANGE_THRESHOLD = 8     # out of 100 sampled positions

# Severity-based cooldowns (seconds)
SEVERITY_COOLDOWNS = {
    "SAFETY": 0,     # Immediate — no cooldown for safety
    "NOTICE": 20,    # Wait 20s between notices
    "INFO": 45,      # Low-priority observations
}
PROACTIVE_PUSHBACK_COOLDOWN = 60   # After user says "stop"/"quiet"
PROACTIVE_MUTE_DURATION = 300      # 5 min mute when user explicitly silences

# Engagement scoring
ENGAGEMENT_INITIAL = 50
ENGAGEMENT_BOOST = 15       # User engaged with observation
ENGAGEMENT_DECAY = 10       # User ignored observation
ENGAGEMENT_MIN = 10
ENGAGEMENT_MAX = 100
ENGAGEMENT_RESPONSE_WINDOW = 30  # seconds to wait for user response

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
    "- Don't list 5 things when one is 90% likely. Lead with the most common cause.\n"
    "- Use words like 'probably', 'usually', '9 times out of 10' — that's how real techs talk.\n"
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
    "- If you don't know, say so in one sentence.\n"
    "- Don't list 5 things when one is 90% likely. Lead with the most common cause.\n"
    "- Use words like 'probably', 'usually', '9 times out of 10' — that's how real techs talk.\n"
)


# ---------------------------------------------------------------------------
# Voice knowledge supplement — brand knowledge, diagnostics, reference data
# Appended to BOTH prompts so voice mode has the same depth as text mode.
# ---------------------------------------------------------------------------

VOICE_KNOWLEDGE = (
    "\n\n## Brand Knowledge\n"
    "- Carrier/Bryant: Flame sensor issues 5-10yr. Board failures 10-15yr. 58 series workhorse furnace.\n"
    "- Trane/American Standard: Built heavy, expensive repair. XV/XR series. ComfortLink proprietary communicating.\n"
    "- Lennox: SLP98/EL296 premium. Quieter, finicky install. Old Pulse furnaces had unique problems.\n"
    "- Rheem/Ruud: Reliable, affordable. Classic Plus, Prestige. Same manufacturer, different distribution.\n"
    "- Goodman/Amana: Budget-friendly, parts everywhere. GMVM97 solid modulating. Amana = premium label, same guts.\n"
    "- Rinnai: Dominates tankless water heaters. Scale buildup is #1 service issue. Error codes well-documented.\n"
    "- AO Smith: Standard tank water heaters. Blink codes on gas models. Vertex = premium condensing line.\n"
    "- Square D: QO = commercial-grade (better trip curves). Homeline = residential. Never mix QO/HOM breakers.\n"
    "- Mitsubishi/Fujitsu/Daikin: Mini-split leaders. Error codes on remote or indoor unit LEDs. Refrigerant charge critical.\n\n"

    "## Diagnostic Approach\n"
    "1. Identify symptom (no heat, no cool, tripping breaker, leak, error code)\n"
    "2. Identify system (brand, model, approximate age, fuel type)\n"
    "3. Start with the MOST COMMON cause for this symptom on this equipment\n"
    "4. Give steps in order of likelihood — cheapest/easiest check first\n"
    "5. If they already checked something, skip it and move to next cause\n\n"

    "## Error Code Rules — CRITICAL\n"
    "- For ANY error code, blink code, or fault code: USE lookup_error_code tool FIRST. ALWAYS. No exceptions.\n"
    "- NEVER guess error code meanings. A wrong code sends a tech down the wrong path and wastes hours.\n"
    "- If lookup returns nothing: 'I don't have that code memorized for [brand]. What does the chart on the unit show?'\n"
    "- Getting an error code wrong is the WORST thing you can do. Say 'I don't know' before guessing.\n"
    "- If VERIFIED ERROR CODE DATA is provided below, use EXACTLY that information.\n\n"

    "## Wire Sizing (NEC Quick Reference)\n"
    "15A→14AWG, 20A→12AWG, 30A→10AWG, 40A→8AWG, 50A→6AWG, 60A→6AWG, 100A→3AWG\n"
    "Over 50ft: bump up one size per 50ft for voltage drop. Always verify local code.\n\n"

    "## Refrigerant Reference\n"
    "R-410A: ~120 PSI suction / 350 PSI discharge at 95°F ambient. Standard since 2010.\n"
    "R-22: Phased out. ~68 PSI suction / 250 PSI discharge at 75°F. Discuss retrofit/replacement.\n"
    "Superheat: 10-15°F (cap tube/piston). Subcooling: 8-12°F (TXV). Always weigh in refrigerant.\n\n"

    "## Plumbing Reference\n"
    "Water heater: 120°F residential, 140°F commercial/dishwasher.\n"
    "Gas pipe: 3/4\" black iron ≈ 150k BTU at 20ft. Tankless: 3/4\" gas minimum, some need 1\".\n"
    "Drain slope: 1/4\" per foot for 2\" and smaller, 1/8\" for 3\" and larger.\n"
    "Copper soldering: Lead-free on potable water. Clean, flux, heat fitting not solder.\n"
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
        self._last_proactive_severity: str = "NOTICE"
        self._user_pushback_count: int = 0
        self._proactive_enabled: bool = True
        self._proactive_muted_until: float = 0  # timestamp when mute expires
        self._last_user_speech_time: float = 0
        # Conversation context for proactive analyzer
        self._conversation_context: list[dict] = []  # last N exchanges
        # Engagement tracking
        self._engagement_score: int = ENGAGEMENT_INITIAL
        self._awaiting_engagement: bool = False  # True after proactive speak
        self._engagement_timer_start: float = 0
        self._last_observation_text: str = ""
        self._observations_ignored: int = 0  # consecutive ignores
        # Category-based de-duplication
        self._observation_categories: dict[str, float] = {}  # category → timestamp
        # Error code pre-injection tracking
        self._has_injected_codes: bool = False

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

async def _analyze_frame_proactive(
    frame_b64: str,
    recent_observations: list[str],
    conversation_context: list[dict] | None = None,
) -> Optional[tuple[str, str, str]]:
    """
    Analyze a frame for proactive monitoring.
    Returns: (severity, observation, category) or None if nothing notable.
    severity: "SAFETY", "NOTICE", or "INFO"
    category: "safety", "error_code", "model_number", "condition", "part_id", "tip"
    """
    client = _get_anthropic_client()

    obs_context = ""
    if recent_observations:
        obs_context = f"\nYou already mentioned: {'; '.join(recent_observations[-3:])}. Don't repeat these."

    conv_context = ""
    if conversation_context:
        lines = []
        for msg in conversation_context[-3:]:
            role = "Tech" if msg.get("role") == "user" else "You"
            lines.append(f"- {role}: {msg.get('content', '')[:80]}")
        conv_context = f"\nRecent conversation:\n" + "\n".join(lines) + "\nDon't repeat what was just discussed.\n"

    response = await asyncio.wait_for(
        client.messages.create(
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
                            f"{conv_context}{obs_context}\n\n"
                            "RESPOND IN THIS EXACT FORMAT (one line):\n"
                            "SEVERITY|CATEGORY|observation\n\n"
                            "SEVERITY must be one of:\n"
                            "- SAFETY: Immediate danger — exposed wiring, gas indicators, active leak, no disconnect, fire hazard\n"
                            "- NOTICE: Worth mentioning — wrong part, corrosion, code violation, readable model/serial number, dirty coils\n"
                            "- INFO: Low priority — general observation, equipment brand visible, helpful tip\n\n"
                            "CATEGORY must be one of: safety, error_code, model_number, condition, part_id, tip\n\n"
                            "RULES:\n"
                            "- ONE observation per frame, ONE short sentence\n"
                            "- If nothing notable, respond with exactly: NOTHING\n"
                            "- Be confident about what you see, hedge on what you're guessing\n"
                        "- A shadow is not a leak. A stain is not active water.\n\n"
                        "Examples:\n"
                        "SAFETY|safety|That wire's exposed and live — kill the breaker before you touch anything.\n"
                        "NOTICE|condition|Those coils look pretty caked up, might want to clean those.\n"
                        "NOTICE|model_number|I can see that's a Carrier 24ACC636 on the data plate.\n"
                        "INFO|tip|That's a Goodman — check the capacitor, they run small from the factory."
                    ),
                },
            ],
        }],
        ),
        timeout=15.0,  # Don't let proactive analysis hang the monitor
    )
    result = response.content[0].text.strip()

    # Parse "NOTHING"
    if result.upper() == "NOTHING" or len(result) < 5:
        return None
    if "nothing" in result.lower() and len(result) < 30:
        return None
    if "don't see" in result.lower() or "can't see" in result.lower():
        return None

    # Parse structured response: SEVERITY|CATEGORY|observation
    parts = result.split("|", 2)
    if len(parts) == 3:
        severity = parts[0].strip().upper()
        category = parts[1].strip().lower()
        observation = parts[2].strip()

        # Validate severity
        if severity not in ("SAFETY", "NOTICE", "INFO"):
            severity = "NOTICE"
        # Validate category
        valid_categories = {"safety", "error_code", "model_number", "condition", "part_id", "tip"}
        if category not in valid_categories:
            category = "condition"

        return (severity, observation, category)

    # Fallback: unstructured response — treat as NOTICE
    return ("NOTICE", result, "condition")


def _get_speech_instruction(severity: str, observation: str, agent: "ArrivalAgent") -> str:
    """Generate varied, natural speech instructions based on severity and context."""
    obs_count = len(agent._recent_observations)
    time_since_last = time.time() - agent._last_proactive_time if agent._last_proactive_time else 999

    if severity == "SAFETY":
        return f"Alert the tech immediately — this is a safety issue: {observation}"
    elif obs_count == 0:
        # First observation on this job
        return f"You just got a look at what they're working on. Mention casually: {observation}"
    elif time_since_last < 60:
        # Recent follow-up
        return f"While they're still working on this, you also noticed: {observation}"
    else:
        # After a long pause
        return f"Hey, one more thing you're seeing: {observation}"


async def proactive_monitor(agent: ArrivalAgent, session: AgentSession):
    """Background task: continuously watches camera and speaks up when something's notable.

    Human-like behavior:
    - Safety observations interrupt immediately, regardless of cooldown
    - Notice/Info observations wait for natural pauses
    - Adapts frequency based on whether user engages with observations
    - Tracks observation categories to avoid repeating the same type
    - Uses varied, natural speech patterns
    """
    logger.info("[proactive] Monitor started — waiting for greeting to finish...")

    await asyncio.sleep(6)

    last_analysis_time = 0

    while True:
        try:
            await asyncio.sleep(PROACTIVE_CHECK_INTERVAL)

            if not agent._proactive_enabled or not agent._room_name:
                continue

            now = time.time()

            # Check if muted (user said "stop"/"quiet")
            if now < agent._proactive_muted_until:
                continue

            # Check engagement — if we're waiting for user response
            if agent._awaiting_engagement:
                elapsed = now - agent._engagement_timer_start
                if elapsed > ENGAGEMENT_RESPONSE_WINDOW:
                    # User didn't respond — decrease engagement
                    agent._observations_ignored += 1
                    agent._engagement_score = max(
                        ENGAGEMENT_MIN,
                        agent._engagement_score - ENGAGEMENT_DECAY
                    )
                    agent._awaiting_engagement = False
                    logger.debug(f"[proactive] Observation ignored (#{agent._observations_ignored}), engagement={agent._engagement_score}")

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

            # Analyze with conversation context
            last_analysis_time = now
            new_hash = agent._frame_hash(frame)

            try:
                result = await _analyze_frame_proactive(
                    frame,
                    list(agent._recent_observations),
                    conversation_context=list(agent._conversation_context),
                )
            except Exception as e:
                logger.warning(f"[proactive] Vision failed: {e}")
                continue

            # Only update hash after successful analysis (so failed frames get retried)
            agent._last_analyzed_hash = new_hash

            if not result:
                continue

            severity, observation, category = result

            # Severity-based cooldown check
            cooldown = SEVERITY_COOLDOWNS.get(severity, 20)

            # Adjust cooldown by engagement score (higher engagement = shorter cooldowns)
            if severity != "SAFETY":
                engagement_factor = agent._engagement_score / ENGAGEMENT_INITIAL  # 0.2 to 2.0
                cooldown = int(cooldown / max(engagement_factor, 0.5))

                # Extra cooldown after pushback
                if agent._user_pushback_count > 2:
                    cooldown = max(cooldown, PROACTIVE_PUSHBACK_COOLDOWN)

            if severity != "SAFETY" and (now - agent._last_proactive_time) < cooldown:
                continue

            # Don't interrupt active conversation (except for SAFETY)
            if severity != "SAFETY" and (now - agent._last_user_speech_time) < 6:
                continue

            # Category-based de-duplication (safety never suppressed)
            if severity != "SAFETY" and category in agent._observation_categories:
                last_category_time = agent._observation_categories[category]
                if now - last_category_time < 60:
                    continue

            # String-based de-duplication
            is_repeat = any(
                obs.lower() in observation.lower() or observation.lower() in obs.lower()
                for obs in agent._recent_observations[-3:]
            )
            if is_repeat and severity != "SAFETY":
                continue

            # ── Speak the observation ──
            instruction = _get_speech_instruction(severity, observation, agent)
            logger.info(f"[proactive] ★ [{severity}|{category}] {observation}")

            await session.generate_reply(instructions=instruction)

            # Update state
            agent._last_proactive_time = now
            agent._last_proactive_severity = severity
            agent._last_observation_text = observation
            agent._recent_observations.append(observation)
            if len(agent._recent_observations) > 5:
                agent._recent_observations.pop(0)
            agent._observation_categories[category] = now

            # Start engagement timer (did user respond to this?)
            agent._awaiting_engagement = True
            agent._engagement_timer_start = now

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

        # Select prompt based on mode — append VOICE_KNOWLEDGE for brand/diagnostic depth
        prompt = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE

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

        # Track user speech for proactive monitor + engagement + mute detection
        # Only match mute/pushback in SHORT utterances to avoid false positives
        # (e.g., "stop valve" or "it's fine copper tubing" should NOT trigger)
        _MUTE_PHRASES = {"stop", "shut up", "quiet", "be quiet", "enough", "shh", "hush", "stop talking"}
        _PUSHBACK_PHRASES = {"it's fine", "that's fine", "not an issue", "i know", "already know", "don't worry"}

        @session.on("user_input_transcribed")
        def on_user_speech(ev):
            agent._last_user_speech_time = time.time()
            transcript = getattr(ev, "text", "") or getattr(ev, "transcript", "") or ""
            if not transcript:
                return

            text_lower = transcript.lower().strip()

            # Store conversation context (for proactive analyzer)
            agent._conversation_context.append({"role": "user", "content": transcript})
            if len(agent._conversation_context) > 6:
                agent._conversation_context.pop(0)

            # Pre-inject error code data so LLM has it without needing a tool call.
            # lookup_error_code is a fast dict lookup — no async/network needed.
            error_result = lookup_error_code(transcript)
            if error_result:
                code_context = format_error_code_context(error_result)
                base = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                agent.instructions = base + (
                    f"\n\n## VERIFIED ERROR CODE — USE THIS EXACTLY:\n{code_context}"
                )
                agent._has_injected_codes = True
                logger.info(f"[arrival-agent] ★ Pre-injected error code for: {transcript[:50]}")
            elif agent._has_injected_codes:
                # Clear stale injection so next non-code question gets clean prompt
                agent.instructions = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                agent._has_injected_codes = False

            # Detect mute commands — only on short utterances (< 6 words)
            # to avoid false positives like "stop valve" or "that's quiet today"
            word_count = len(text_lower.split())
            if word_count <= 5 and any(phrase in text_lower for phrase in _MUTE_PHRASES):
                agent._proactive_muted_until = time.time() + PROACTIVE_MUTE_DURATION
                agent._awaiting_engagement = False
                logger.info(f"[proactive] Muted for {PROACTIVE_MUTE_DURATION}s — user said: '{text_lower}'")
                return

            # Detect pushback — only on short utterances (< 8 words)
            if word_count <= 7 and any(phrase in text_lower for phrase in _PUSHBACK_PHRASES):
                agent._user_pushback_count += 1
                agent._awaiting_engagement = False
                logger.info(f"[proactive] Pushback #{agent._user_pushback_count} — user said: '{text_lower}'")
                return

            # Engagement detection — did user respond to our observation?
            if agent._awaiting_engagement and agent._last_observation_text:
                elapsed = time.time() - agent._engagement_timer_start
                if elapsed < ENGAGEMENT_RESPONSE_WINDOW:
                    # Check if response is related (simple keyword overlap)
                    obs_words = set(agent._last_observation_text.lower().split())
                    user_words = set(text_lower.split())
                    overlap = (obs_words & user_words) - {"the", "a", "is", "it", "that", "this", "i", "you", "and", "or", "to"}
                    if len(overlap) >= 1 or "?" in transcript:
                        # User engaged! Boost engagement score
                        agent._engagement_score = min(ENGAGEMENT_MAX, agent._engagement_score + ENGAGEMENT_BOOST)
                        agent._observations_ignored = 0
                        # Reset pushback when user is actively engaging
                        if agent._user_pushback_count > 0:
                            agent._user_pushback_count = max(0, agent._user_pushback_count - 1)
                        agent._awaiting_engagement = False
                        logger.info(f"[proactive] User engaged (overlap: {overlap}), engagement={agent._engagement_score}")

        # Track assistant responses for conversation context
        @session.on("agent_speech_committed")
        def on_agent_speech(ev):
            text = getattr(ev, "text", "") or getattr(ev, "content", "") or ""
            if text:
                agent._conversation_context.append({"role": "assistant", "content": text})
                if len(agent._conversation_context) > 6:
                    agent._conversation_context.pop(0)

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
