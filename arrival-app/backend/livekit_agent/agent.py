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
import random
import re
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
from livekit import rtc
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
# Shared clients — reused across all calls to avoid per-request overhead
# ---------------------------------------------------------------------------
_anthropic_client: Optional[anthropic_sdk.AsyncAnthropic] = None
_httpx_client: Optional[httpx.AsyncClient] = None

def _get_anthropic_client() -> anthropic_sdk.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic_sdk.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _anthropic_client

def _get_httpx_client() -> httpx.AsyncClient:
    """Shared httpx client for frame fetching — avoids creating a new client every 3-5s."""
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=3.0)
    return _httpx_client

def _frame_to_jpeg(frame: rtc.VideoFrame, quality: int = 50) -> bytes | None:
    """Convert a LiveKit VideoFrame (RGBA) to JPEG bytes."""
    try:
        from PIL import Image
        import io
        img = Image.frombytes("RGBA", (frame.width, frame.height), frame.data)
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except ImportError:
        logger.warning("[video] Pillow not installed — cannot convert video frames")
        return None
    except Exception as e:
        logger.debug(f"[video] JPEG conversion failed: {e}")
        return None

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
PROACTIVE_CHECK_INTERVAL = 5    # seconds between proactive analysis cycles (unused in new 3-state model)
FRAME_CHANGE_THRESHOLD = 8     # out of 100 sampled positions

# Proactive monitor — adaptive intervals
SCENE_POLL_INTERVAL = 15          # Base interval for checking frames (seconds)
SCENE_STATIC_BACKOFF = 60         # Back off to this when nothing changes
SCENE_ACTIVE_INTERVAL = 12        # Check more often when scene is changing
SCENE_POST_SPEAK_COOLDOWN = 30    # Minimum gap between proactive interjections (passive)
GUIDANCE_CHECK_INTERVAL = 8       # Check more often during guidance — actively guiding
GUIDANCE_SPEAK_COOLDOWN = 12      # Guidance can speak more often — user expects it
TASK_CONTEXT_DECAY_SECONDS = 120  # Clear inferred task after 2 min of silence
SCENE_IGNORED_BACKOFF = 45        # If user ignored our last comment, wait this long
PROACTIVE_MUTE_DURATION = 300     # 5 min mute when user explicitly silences

# Task inference patterns — regex-free, fast string matching
_TASK_PHRASES = [
    "i'm replacing", "i'm installing", "i'm checking", "i'm fixing",
    "i'm repairing", "i'm removing", "i'm wiring", "i'm connecting",
    "i'm working on", "i'm looking at", "i'm troubleshooting",
    "im replacing", "im installing", "im checking", "im fixing",
    "im repairing", "im removing", "im wiring", "im connecting",
    "im working on", "im looking at", "im troubleshooting",
    "working on", "need to replace", "need to fix", "need to install",
    "need to repair", "need to check", "trying to fix", "trying to replace",
    "replacing a", "replacing the", "installing a", "installing the",
    "fixing a", "fixing the", "repairing a", "repairing the",
    "hooking up", "swapping out", "putting in",
]

# ---------------------------------------------------------------------------
# Real-Time Guidance config
# ---------------------------------------------------------------------------
GUIDANCE_MAX_STEPS = 12         # Max steps in a guided procedure
GUIDANCE_STEP_VERIFY_TOKENS = 200  # More tokens for detailed step verification


# ---------------------------------------------------------------------------
# Voice prompts
# ---------------------------------------------------------------------------

JOB_MODE_PROMPT = (
    # ── WHO YOU ARE ──
    "You are Arrival — Real Time Guidance for trade workers. See, Reason, Guide. "
    "You see what the worker sees through their phone camera, you reason about it, "
    "and you guide them through the job. You are to physical workers what coding "
    "assistants are to developers — always there, always watching, always ready to help.\n\n"

    "You work with electricians, plumbers, HVAC techs, builders, and all skilled trades. "
    "Tradespeople encounter all kinds of work on a job site — drywall, painting, insulation, "
    "carpentry, you name it. If it comes up on a job, you help with it. Never dismiss anything.\n\n"

    # ── SEE ──
    "SEE — A camera frame is attached to every message as context.\n"
    "- When they ask 'what do you see' or 'what is this': name the thing in 1-5 words. Read any labels. That's it.\n"
    "- For all other questions: just answer. Don't describe the camera.\n"
    "- Never hallucinate objects, wires, or equipment that aren't clearly visible.\n\n"

    # ── REASON ──
    "REASON — Use your knowledge and tools to figure out what's going on.\n"
    "- lookup_error_code: ONLY for error codes, blink codes, fault codes. Try this FIRST when codes are mentioned.\n"
    "- search_knowledge: ONLY for specific technical questions — building codes, specs, sizing, "
    "manuals, installation requirements, manufacturer-specific procedures.\n"
    "- WHEN TO USE TOOLS vs JUST ANSWER:\n"
    "  - 'What do you see?' → look at the frame and answer directly. No tools needed.\n"
    "  - 'What is that?' → look at the frame and answer directly. No tools needed.\n"
    "  - 'What error code is that?' → use lookup_error_code.\n"
    "  - 'What size wire do I need for a 40A circuit?' → use search_knowledge.\n"
    "  - 'Walk me through replacing this capacitor' → use start_guidance to load your knowledge, then guide naturally.\n"
    "  - 'Is this up to code?' → use search_knowledge for the specific code requirement.\n"
    "- Lead with the most likely answer. Don't list 5 possibilities.\n"
    "- Never make something up. If you don't know, say 'I'm not sure on that one.'\n"
    "- For error codes: use lookup_error_code first, then search_knowledge. "
    "If both miss, say 'I don't have that code — what does the chart on the unit show?'\n\n"

    # ── GUIDE ──
    "GUIDE — Walk them through the job naturally.\n"
    "- start_guidance: When they want to be walked through a procedure. "
    "Loads your knowledge of the job so you can guide them like a vet.\n"
    "- You guide by watching the camera and telling them what to do next "
    "based on what you see. No numbered steps. No lists. Just talk.\n"
    "- If you spot a safety issue, wrong part, or bad technique — speak up immediately.\n"
    "- If they confirm or say 'yeah I see it', tell them what's next.\n\n"

    # ── HOW TO TALK ──
    "VOICE — You're spoken aloud. Talk like a coworker, not a manual.\n"
    "- Match length to the question. Short question = short answer. Complex question = full explanation.\n"
    "- No filler. No 'Great question!' No 'Let me know if you need anything.' No repeating their question back.\n"
    "- Lead with the answer. Give specific numbers. Use contractions.\n"
    "- If they push back, back off. If they say stop, go silent.\n"
    "- Never say 'consult a professional' — they ARE the professional.\n"
    "- NEVER start by describing what you see unless they asked. Just answer the question.\n"
    "- ALWAYS spell out units in full — never use abbreviations in your spoken response:\n"
    "  W → watts, kW → kilowatts, A → amps, V → volts, mm → millimetres, cm → centimetres,\n"
    "  m → metres, mm² → millimetre squared, MPa → megapascals, kPa → kilopascals, kg → kilograms\n"
    "- When answering from documents, TRANSLATE the spec into natural speech — never read raw notation.\n"
    "  BAD: 'Kitchen: 6 x LED downlights (10W each) on dimmer circuit'\n"
    "  GOOD: 'Six 10-watt LED downlights in the kitchen, on a dimmer.'\n"
    "  BAD: 'Oven: 32A circuit, 6mm² TPS, direct to sub-board'\n"
    "  GOOD: 'The oven is on a 32-amp circuit with 6-millimetre cable direct to the board.'\n\n"

    # ── EXAMPLES — mirror these patterns ──
    "EXAMPLES of how to respond:\n"
    "Tech: 'What do you see?'\n"
    "You: 'Carrier 58MVC furnace. Light's blinking on the board.'\n\n"
    "Tech: 'How do I turn this on?'\n"
    "You: 'Switch on the side of the unit, flip it up.'\n\n"
    "Tech: 'What size wire for a 40 amp circuit?'\n"
    "You: '8 AWG copper.'\n\n"
    "Tech: 'This thing won't start, what do I check first?'\n"
    "You: 'Check if you've got power at the disconnect. If that's good, check the contactor.'\n\n"
    "Tech: 'Is this up to code?'\n"
    "You: 'Let me check that for you.' [uses search_knowledge]\n\n"

    # ── QUICK REFERENCE ──
    "QUICK REFERENCE:\n"
    "- Superheat (cap tube/fixed orifice): 10-15°F | TXV: measure subcooling 10-12°F\n"
    "- R-410A: ~118 psi suction / ~340 psi discharge @ 75°F\n"
    "- R-22: ~68 psi suction / ~250 psi discharge @ 75°F\n"
    "- Gas: 7\" WC natural gas, 11\" WC propane\n"
    "- Wire: 15A=14AWG, 20A=12AWG, 30A=10AWG, 40A=8AWG, 50A=6AWG\n"
    "- GFCI: bathrooms, kitchen countertops, garages, outdoors, crawlspaces\n"
    "- Drain slope: 1/4\" per foot (2\" and smaller), 1/8\" (3\" and larger)\n"
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
    "\n\n## Error Code Rules — CRITICAL\n"
    "- For ANY error code, blink code, or fault code: USE lookup_error_code tool FIRST. ALWAYS. No exceptions.\n"
    "- NEVER guess error code meanings. A wrong code sends a tech down the wrong path and wastes hours.\n"
    "- If lookup returns nothing: 'I don't have that code memorized for [brand]. What does the chart on the unit show?'\n"
    "- Getting an error code wrong is the WORST thing you can do. Say 'I don't know' before guessing.\n"
    "- If VERIFIED ERROR CODE DATA is provided below, use EXACTLY that information.\n"
)


# ---------------------------------------------------------------------------
# Scene Memory — persistent understanding of what's happening on the job
# ---------------------------------------------------------------------------

class SceneMemory:
    """Maintains a running understanding of the job site scene."""

    def __init__(self):
        self.objects: list[str] = []          # "breaker panel", "wire stripper", "12 AWG romex"
        self.activity: str = ""               # "wiring a 20A circuit"
        self.stage: str = ""                  # "prep", "execution", "testing", "cleanup"
        self.observations_made: list[str] = []  # everything we've said (never repeat)
        self.last_spoken_time: float = 0      # when we last spoke up
        self.last_spoken_text: str = ""       # what we last said
        self.frames_since_change: int = 0     # how many consecutive frames looked the same
        self.last_scene_hash: str = ""        # for frame diffing
        self.ignored_count: int = 0           # times user didn't respond after we spoke
        self.user_responded_after_speak: bool = True  # did user talk after our last interjection
        self.last_updated: float = 0         # when scene was last analyzed (for freshness checks)

    def update_from_analysis(self, objects: list[str], activity: str, stage: str):
        """Update scene understanding from analysis result."""
        self.objects = objects
        if activity:
            self.activity = activity
        if stage:
            self.stage = stage
        self.frames_since_change = 0
        self.last_updated = time.time()

    def record_speech(self, text: str):
        """Record that we spoke — for anti-repeat and cooldown."""
        self.observations_made.append(text)
        if len(self.observations_made) > 20:
            self.observations_made = self.observations_made[-20:]
        self.last_spoken_time = time.time()
        self.last_spoken_text = text

    def already_said(self, text: str) -> bool:
        """Check if we already said something similar."""
        text_lower = text.lower()
        return any(
            obs.lower() in text_lower or text_lower in obs.lower()
            for obs in self.observations_made
        )


# ---------------------------------------------------------------------------
# Agent with tools + always-on vision
# ---------------------------------------------------------------------------

import re as _re_tts

def _clean_for_tts(text: str) -> str:
    """
    Convert technical notation and markdown into clean speakable text.
    ElevenLabs chokes on symbols, superscripts, and markdown formatting.
    """
    # Superscript characters (m², mm², cm³)
    text = text.replace("²", " squared").replace("³", " cubed")
    # Degree symbols
    text = text.replace("°C", " degrees C").replace("°F", " degrees F").replace("°", " degrees ")
    # Electrical/mechanical units — order matters: longest match first
    # kW before W, mm before m, etc.
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*mm²', r'\1 millimetre squared', text)    # 6mm² first
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*mm', r'\1 millimetre', text)             # 6mm
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*cm', r'\1 centimetre', text)             # 10cm
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*m²', r'\1 square metres', text)          # 48m²
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*m\b', r'\1 metres', text)               # 6m
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*kW\b', r'\1 kilowatts', text)           # 5kW before W
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*[Ww]\b', r'\1 watts', text)             # 10W
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*kVA\b', r'\1 kilovolt-amps', text)
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*[Vv]\b', r'\1 volts', text)             # 240V
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*[Aa]\b', r'\1 amps', text)              # 32A
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*MPa\b', r'\1 megapascals', text)
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*kPa\b', r'\1 kilopascals', text)
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*kg\b', r'\1 kilograms', text)
    text = _re_tts.sub(r'(\d+(?:\.\d+)?)\s*psi\b', r'\1 PSI', text)
    text = _re_tts.sub(r'\bTPS\b', 'TPS cable', text)
    text = _re_tts.sub(r'\bGPO\b', 'power outlet', text)
    # Markdown bold/italic — strip asterisks and underscores
    text = _re_tts.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = _re_tts.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    # Markdown bullet points and hashes
    text = _re_tts.sub(r'^#+\s+', '', text, flags=_re_tts.MULTILINE)
    text = _re_tts.sub(r'^\s*[-•*]\s+', '', text, flags=_re_tts.MULTILINE)
    # Inline code backticks
    text = _re_tts.sub(r'`([^`]+)`', r'\1', text)
    # Fraction-style specs like "4/12/4" — leave as-is, TTS handles numbers fine
    # Strip leftover brackets from doc references like [Source: ...]
    text = _re_tts.sub(r'\[Source:[^\]]*\]', '', text)
    text = _re_tts.sub(r'\[Reference docs[^\]]*\]', '', text)
    # Collapse multiple spaces/newlines
    text = _re_tts.sub(r'\n+', ' ', text)
    text = _re_tts.sub(r'  +', ' ', text)
    return text.strip()


class ArrivalAgent(Agent):
    """Trade worker voice agent with error code lookup, always-on vision, and proactive monitoring."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # User context — populated from participant metadata at session start
        self._user_id: str = "unknown"
        self._team_id: Optional[str] = None
        self._active_job: Optional[str] = None  # e.g. "Fladgate residence"
        # Camera state — frames come from data channel OR HTTP frame store
        self._latest_frame: Optional[str] = None
        self._frame_received_at: float = 0
        self._room_name: str = ""
        self._room = None
        # Proactive vision state
        self._proactive_enabled: bool = True
        self._proactive_muted_until: float = 0  # timestamp when mute expires
        self._last_user_speech_time: float = 0
        self._user_pushback_count: int = 0
        # Scene memory — persistent understanding of the job
        self._scene: SceneMemory = SceneMemory()
        # Conversation context for proactive analyzer
        self._conversation_context: list[dict] = []  # last N exchanges
        # Error code pre-injection tracking
        self._has_injected_codes: bool = False
        # Real-Time Guidance state
        self._guidance_active: bool = False
        self._guidance_task: str = ""           # "replacing capacitor on Carrier 24ACC"
        self._guidance_brief: str = ""          # knowledge brief (not numbered steps)
        self._guidance_context: str = ""        # RAG context for the procedure
        # Equipment context (sent from frontend)
        self._equipment_type: str = ""
        self._equipment_brand: str = ""
        self._equipment_model: str = ""
        # Task context — inferred from conversation for context-grounded proactive vision
        self._inferred_task: str = ""
        self._inferred_task_updated_at: float = 0
        # Session-level classification — runs once each
        self._task_type: str = ""                 # diagnostic/install/repair/inspect/maintenance
        self._task_type_classified: bool = False
        self._environment_type: str = ""          # indoor/outdoor
        self._environment_setting: str = ""       # residential/commercial/industrial
        self._environment_space: str = ""         # attic/crawlspace/panel/rooftop/etc
        self._environment_classified: bool = False

    def get_guidance_state(self) -> dict:
        """Serialize guidance state for persistence/data channel."""
        if not self._guidance_active:
            return {"active": False}
        return {
            "active": True,
            "task": self._guidance_task,
            "brief": self._guidance_brief,
        }

    def restore_guidance_state(self, state: dict):
        """Restore guidance state from data channel (on reconnect)."""
        if not state.get("active"):
            return
        self._guidance_active = True
        self._guidance_task = state.get("task", "")
        self._guidance_brief = state.get("brief", "")
        logger.info(f"[guidance] ✓ Restored guidance state for '{self._guidance_task}'")

    def update_camera_frame(self, frame_b64: str):
        """Store the latest camera frame from the mobile app."""
        self._latest_frame = frame_b64
        self._frame_received_at = time.time()
        frame_kb = len(frame_b64) * 3 // 4 // 1024
        logger.info(f"[frame] Received via data channel: {frame_kb}KB, {len(frame_b64)} chars")

    async def get_current_frame(self) -> Optional[str]:
        """Get the best available frame — tries data channel, HTTP, file store."""
        # 1. Data channel frame (if recent) — fastest
        if self._latest_frame and (time.time() - self._frame_received_at) < 4:
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

        # 4. No fresh frame available — return None rather than a stale frame
        return None

    async def _fetch_frame_async(self, room_name: str) -> Optional[str]:
        """Fetch frame via async HTTP using shared client."""
        try:
            client = _get_httpx_client()
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
        if not self._scene.last_scene_hash:
            return True
        diff = sum(a != b for a, b in zip(new_hash, self._scene.last_scene_hash))
        return diff > FRAME_CHANGE_THRESHOLD

    def _equipment_context_str(self) -> str:
        """Build equipment context string for prompts."""
        parts = []
        if self._equipment_type:
            parts.append(self._equipment_type.replace("_", " "))
        if self._equipment_brand:
            parts.append(self._equipment_brand)
        if self._equipment_model:
            parts.append(f"model {self._equipment_model}")
        return ", ".join(parts) if parts else ""

    def tts_node(self, text, model_settings):
        """Strip robotic filler and clean technical symbols before TTS speaks it."""
        filtered = self._filter_robotic_text(text)
        return Agent.default.tts_node(self, filtered, model_settings)

    async def _filter_robotic_text(self, text):
        """Async generator that strips AI filler from the text stream."""
        import re

        # Filler at the START of a response
        _FILLER_START = re.compile(
            r"(?i)^(okay,?\s*so,?\s*|alright,?\s*so,?\s*|sure!?\s*|"
            r"great question!?\s*|that's a great question\.?\s*|"
            r"good question\.?\s*|absolutely!?\s*|of course!?\s*|"
            r"well,?\s*|so,?\s*|now,?\s*|right,?\s*so,?\s*)"
        )
        # Robotic phrases anywhere
        _ROBOTIC = re.compile(
            r"(?i)("
            r"it'?s important to note that|it'?s worth noting that|"
            r"i'?d recommend|i would recommend|i'?d suggest|"
            r"let me know if you (?:need|have|want) anything.*?[.!]|"
            r"hope that helps.*?[.!]|does that make sense\??|"
            r"feel free to|don'?t hesitate to|"
            r"if you have any (?:other )?questions.*?[.!]|"
            r"happy to help.*?[.!]|"
            r"in summary,? |to summarize,? |in conclusion,? |"
            r"(?:here'?s |here is )(?:what|the thing|a quick)|"
            r"that being said,? |with that in mind,? |"
            r"it'?s also worth mentioning that |"
            r"(?:please )?keep in mind that |"
            r"as (?:always|a reminder),? |"
            r"just to (?:be clear|clarify),? |"
            r"what you(?:'re| are) going to want to do is |"
            r"what you(?:'ll)? want to do is |"
            r"so basically,? |"
            r"the (?:first|main|key) thing (?:to do |is )|"
            r"you(?:'re| are) going to (?:want|need) to |"
            r"i(?:'d| would) (?:also )?like to (?:point out|mention|note) (?:that )?|"
            r"for (?:this|that) (?:particular |specific )?(?:task|job|situation),? |"
            r"in (?:this|that) case,? "
            r")"
        )
        # Numbered/step patterns — "Step 1:", "1.", "1)", "First,", "Second,"
        # These get converted to natural speech: remove the number, keep the content
        _NUMBERED = re.compile(
            r"(?i)(?:step\s+\d+[:.]\s*|\d+[.)]\s*|first(?:ly)?,?\s+|second(?:ly)?,?\s+|"
            r"third(?:ly)?,?\s+|fourth(?:ly)?,?\s+|fifth(?:ly)?,?\s+|"
            r"next,?\s+|finally,?\s+|lastly,?\s+|additionally,?\s+|"
            r"furthermore,?\s+|moreover,?\s+)"
        )

        buffer = ""
        is_start = True
        sentence_count = 0
        MAX_VOICE_SENTENCES = 3  # Hard cap — keep answers tight for voice

        async for chunk in text:
            # Stop generating after max sentences
            if sentence_count >= MAX_VOICE_SENTENCES:
                break

            buffer += chunk

            # Wait for enough text to process
            if len(buffer) < 20 and not any(c in chunk for c in ".!?\n"):
                continue

            if is_start:
                buffer = _FILLER_START.sub("", buffer)
                if buffer.strip():
                    is_start = False

            buffer = _ROBOTIC.sub("", buffer)
            buffer = _NUMBERED.sub("", buffer)
            buffer = _clean_for_tts(buffer)
            buffer = re.sub(r"  +", " ", buffer)

            if buffer.strip():
                # Count sentences — only terminal punctuation (not decimals like 17.5)
                import re as _re_s
                sentence_count += len(_re_s.findall(r'(?<!\d)\.(?!\d)|[!?]', buffer))
                yield buffer
                buffer = ""

        if buffer.strip() and sentence_count < MAX_VOICE_SENTENCES:
            buffer = _ROBOTIC.sub("", buffer)
            buffer = _NUMBERED.sub("", buffer)
            buffer = _clean_for_tts(buffer)
            buffer = re.sub(r"  +", " ", buffer).strip()
            if buffer:
                yield buffer

    async def on_user_turn_completed(self, turn_ctx, new_message):
        """Inject the latest camera frame with aggressive context management.

        Key insight: for a job-site voice assistant, old conversation turns are
        noise. The model must see the CURRENT frame and respond to it fresh —
        not anchor on what it said 3 turns ago. We:
        1. Truncate to last 4 items (2 user-assistant pairs + system prompt)
        2. Strip ALL images from remaining history
        3. DELETE (not replace) old vision descriptions — replacing with a note
           like 'camera moved' still primes the model to anchor on old content
        """
        from livekit.agents.llm import ImageContent

        # Track user speech for proactive monitor ignore detection
        self._last_user_speech_time = time.time()
        if hasattr(self, '_scene'):
            self._scene.user_responded_after_speak = True
            self._scene.ignored_count = max(0, self._scene.ignored_count - 1)  # Forgive one ignore per interaction

        # 1. Truncate — prevents unbounded context growth
        #    Keep 8 items (4 user-assistant pairs) for better context/intelligence
        #    Old images are stripped below so they don't anchor the model
        turn_ctx.truncate(max_items=8)

        # 2. Strip old images + vision descriptions from remaining history
        _VISION_PHRASES = (
            "i can see", "i see", "looks like", "you're looking at",
            "i'm looking at", "in the frame", "in the image",
            "the camera shows", "showing you", "appears to be",
            "that's a", "that looks like", "what i see",
            "camera description", "camera has moved",
        )
        for msg in turn_ctx.items:
            if msg is new_message:
                continue
            if not hasattr(msg, 'content'):
                continue

            # Remove images and camera labels from all old messages
            if isinstance(msg.content, list):
                msg.content = [
                    c for c in msg.content
                    if not isinstance(c, ImageContent)
                    and not (isinstance(c, str) and "CAMERA" in c)
                ]

            # For assistant messages: delete vision descriptions entirely
            if hasattr(msg, 'role') and msg.role == 'assistant':
                text = ""
                if isinstance(msg.content, str):
                    text = msg.content
                elif isinstance(msg.content, list):
                    text = " ".join(c for c in msg.content if isinstance(c, str))
                if any(phrase in text.lower() for phrase in _VISION_PHRASES):
                    msg.content = []  # Gone — no residue, no anchoring

        # 3. Inject current frame onto the new message
        #    Use cached frame (updated by WebRTC video processor at ~3fps).
        #    HTTP fallback only if cache is stale — avoids blocking on slow HTTP.
        frame = self._latest_frame if (
            self._latest_frame and (time.time() - self._frame_received_at) < 8
        ) else None
        if not frame:
            frame = await self.get_current_frame()
        if frame:
            data_url = f"data:image/jpeg;base64,{frame}"
            image_content = ImageContent(image=data_url)
            eq_str = self._equipment_context_str()

            # Check if user is asking a vision question
            user_text = ""
            if isinstance(new_message.content, str):
                user_text = new_message.content.lower()
            elif isinstance(new_message.content, list):
                user_text = " ".join(c.lower() for c in new_message.content if isinstance(c, str))

            _VISION_QUESTIONS = (
                "what do you see", "what is this", "what is that", "what am i looking at",
                "what's this", "what's that", "can you see", "do you see", "look at this",
                "what are these", "what are those", "identify", "read this", "read that",
                "what does this say", "what does that say", "what brand", "what model",
            )
            is_vision_question = any(q in user_text for q in _VISION_QUESTIONS)

            # Ensure content is a list (SDK may pass string or list)
            if isinstance(new_message.content, str):
                new_message.content = [new_message.content]
            elif not isinstance(new_message.content, list):
                new_message.content = [new_message.content]

            if is_vision_question:
                # Vision question: image first so model focuses on describing
                new_message.content = [image_content] + new_message.content
            else:
                # Non-vision question: text first, image is just background context
                new_message.content = new_message.content + [image_content]
                if eq_str:
                    new_message.content.append(f" [Equipment: {eq_str}]")
        else:
            logger.warning(f"[vision-debug] NO FRAME (age={time.time() - self._frame_received_at:.1f}s)")

        # 4. Guidance brief is injected via system prompt in on_user_speech (line ~1676-1687)
        # No need to also append it to every message — that wastes tokens/money.

        # 4b. Auto-RAG: search company docs + knowledge base for EVERY query
        # Don't rely on LLM deciding to call search_knowledge tool — inject automatically.
        try:
            user_text_for_rag = ""
            if isinstance(new_message.content, str):
                user_text_for_rag = new_message.content
            elif isinstance(new_message.content, list):
                user_text_for_rag = " ".join(c for c in new_message.content if isinstance(c, str))

            # Skip RAG for very short utterances (greetings, "yes", "ok", "thanks")
            if len(user_text_for_rag.strip()) > 10:
                # Prefix query with active job name so it surfaces job-specific docs
                rag_query = user_text_for_rag
                if self._active_job:
                    rag_query = f"{self._active_job}: {user_text_for_rag}"
                rag_results = await retrieve_context(
                    user_id=self._user_id,
                    query=rag_query,
                    top_k=3,
                    team_id=self._team_id,
                )
                if rag_results:
                    job_lines = []
                    knowledge_lines = []
                    for r in rag_results:
                        label = f"[{r.get('filename', 'doc')}]"
                        entry = f"{label} {r.get('text', '')}"
                        if r.get("is_personal"):
                            job_lines.append(entry)
                        else:
                            knowledge_lines.append(entry)
                    parts = []
                    if job_lines:
                        parts.append("[UPLOADED JOB DOCS — use for job-specific specs, plans, measurements]\n" + "\n".join(job_lines))
                    if knowledge_lines:
                        parts.append("[TRADE KNOWLEDGE — use for codes, procedures, general specs]\n" + "\n".join(knowledge_lines))
                    rag_inject = "\n\n".join(parts)
                    if isinstance(new_message.content, list):
                        new_message.content.append(rag_inject)
                    else:
                        new_message.content = [new_message.content, rag_inject]
                    logger.info(f"[rag-auto] Injected {len(rag_results)} results for: {user_text_for_rag[:50]}")
        except Exception as e:
            logger.debug(f"[rag-auto] Failed: {e}")

        # 5. Trigger spatial recording if consent given
        if getattr(self, '_spatial_recorder', None):
            # Extract user text for trigger
            trigger_text = ""
            if isinstance(new_message.content, str):
                trigger_text = new_message.content
            elif isinstance(new_message.content, list):
                trigger_text = " ".join(c for c in new_message.content if isinstance(c, str))
            asyncio.ensure_future(
                self._spatial_recorder.trigger_recording(
                    trigger_type='user_query',
                    trigger_text=trigger_text,
                    agent=self,
                )
            )

        # 5. Also truncate the persistent context to prevent unbounded growth
        #    (the copy we modified above is used for this LLM call; this keeps
        #    the agent's internal context lean for future calls)
        try:
            persistent_ctx = self.chat_ctx.copy()
            persistent_ctx.truncate(max_items=10)
            await self.update_chat_ctx(persistent_ctx)
        except Exception:
            pass  # Non-critical — the per-call truncation above is what matters

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
        logger.info(f"[arrival-agent] Knowledge search: {query} (user={self._user_id[:8] if self._user_id else '?'} team={self._team_id or 'none'})")
        try:
            results = await retrieve_context(
                user_id=self._user_id,
                query=query,
                top_k=3,
                team_id=self._team_id,
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
    async def start_guidance(self, task_description: str) -> str:
        """Start Real-Time Guidance for a task. Use when the tech asks you to walk them
        through something, guide them, or help them do a procedure.
        Examples: 'walk me through replacing this capacitor', 'guide me through this install',
        'help me with this', 'what do I do first'."""
        logger.info(f"[guidance] ★ Starting guidance: {task_description}")

        # If no task specified, ask what they need help with
        if not task_description or len(task_description.strip()) < 3:
            return (
                "The tech wants guidance but hasn't said what they need help with. "
                "Ask them naturally: 'What are you working on?' or 'What do you need a hand with?' "
                "Once they tell you, call start_guidance with their task."
            )

        # 1. Search knowledge base for relevant procedure
        rag_context = ""
        try:
            results = await retrieve_context(
                user_id=self._user_id,
                query=task_description,
                top_k=5,
                team_id=self._team_id,
            )
            if results:
                parts = []
                for r in results:
                    source = r.get("filename", "knowledge base")
                    text = r.get("text", "")
                    parts.append(f"[{source}]\n{text}")
                rag_context = "\n\n---\n\n".join(parts)
        except Exception as e:
            logger.warning(f"[guidance] RAG search failed: {e}")

        # 2. Generate a knowledge brief — NOT numbered steps
        client = _get_anthropic_client()
        eq_str = self._equipment_context_str()
        eq_note = f"\nEquipment: {eq_str}\n" if eq_str else ""

        brief_prompt = (
            "A trade worker is on-site with their phone camera. They need guidance on a task. "
            "You need to write a KNOWLEDGE BRIEF — everything a veteran tradesman would "
            "have in their head before starting this job.\n\n"
            f"TASK: {task_description}\n{eq_note}\n"
        )
        if rag_context:
            brief_prompt += f"REFERENCE MATERIAL:\n{rag_context}\n\n"

        brief_prompt += (
            "Write a concise knowledge brief with these sections:\n"
            "SAFETY: What to shut off/lock out/verify before touching anything\n"
            "WHAT YOU NEED: Specific tools and parts (⅜ wrench, not 'appropriate tool')\n"
            "THE JOB: What needs to happen, in the order it happens — written as prose, "
            "how a vet would explain it over the phone. NOT numbered steps.\n"
            "GOTCHAS: Common mistakes, things that catch people out\n"
            "DONE RIGHT: How to verify the job is done correctly\n\n"
            "Keep it tight. No fluff. Write it how a tradesman thinks about a job, "
            "not how a manual documents it. Skip sections that don't apply.\n"
            "Example for 'replacing a capacitor':\n"
            "SAFETY: Kill power at disconnect, verify 0V both legs with meter\n"
            "WHAT YOU NEED: Insulated screwdriver, new cap (match μF and voltage rating exactly), "
            "phone camera to photo the wiring before disconnecting\n"
            "THE JOB: Discharge the old cap by shorting terminals with insulated screwdriver. "
            "Photo the wiring. Pull the old cap, note the ratings on the label. "
            "Wire the new one exactly the same way — Common to C, Herm to compressor, Fan to fan motor.\n"
            "GOTCHAS: If you wire Herm and Fan backwards, compressor runs but fan doesn't. "
            "Some caps have different terminal layouts even with same ratings.\n"
            "DONE RIGHT: Power on, compressor and fan both start, amp draw is normal."
        )

        try:
            response = await client.messages.create(
                model=config.ANTHROPIC_VISION_MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": brief_prompt}],
            )
            brief = response.content[0].text.strip()
        except Exception as e:
            logger.error(f"[guidance] Failed to generate brief: {e}")
            return "I couldn't put together guidance for that. Just tell me what you're working on and I'll talk you through it."

        # 3. Activate guidance mode
        self._guidance_active = True
        self._guidance_task = task_description
        self._guidance_brief = brief
        self._guidance_context = rag_context
        # Set task context for proactive vision
        self._inferred_task = task_description
        self._inferred_task_updated_at = time.time()

        # Start spatial sequence for this guided job — include equipment + task_type
        if getattr(self, '_spatial_recorder', None):
            equip = {"type": self._equipment_type, "brand": self._equipment_brand, "model": self._equipment_model} if hasattr(self, '_equipment_type') else None
            asyncio.ensure_future(self._spatial_recorder.start_sequence(
                task_description, equip, task_type=self._task_type
            ))

        logger.info(f"[guidance] ✓ Knowledge brief generated for: {task_description}")
        logger.info(f"[guidance]   Brief: {brief[:200]}...")

        return (
            f"GUIDANCE ACTIVE — Task: {task_description}\n\n"
            f"KNOWLEDGE BRIEF:\n{brief}\n\n"
            "HOW TO GUIDE:\n"
            "- You now know this job inside out. Guide them naturally based on what you "
            "see on camera, like a vet standing next to them.\n"
            "- Tell them what to do FIRST right now. One thing at a time.\n"
            "- When you see they've done something, tell them what's next.\n"
            "- NEVER say 'step 1', 'step 2', or use numbered lists. Just talk.\n"
            "- Reference what you see: 'See that silver cylinder? That's your cap.'\n"
            "- If they ask a question mid-task, answer it and pick up where you left off.\n"
            "- When the job looks done, tell them how to verify it.\n"
            "Start by telling them the very first thing to do."
        )

    @function_tool()
    async def stop_guidance(self) -> str:
        """Stop the current guidance session. Use when the tech says 'stop', 'I'm done',
        'that's enough', 'nevermind', or when the job is clearly finished."""
        if not self._guidance_active:
            return "No active guidance to stop."
        task = self._guidance_task
        self._guidance_active = False
        self._guidance_task = ""
        self._guidance_brief = ""
        self._guidance_context = ""
        # End spatial sequence with frame comparison
        if getattr(self, '_spatial_recorder', None):
            asyncio.ensure_future(self._spatial_recorder._compare_sequence_frames(self))
            asyncio.ensure_future(self._spatial_recorder.end_sequence(outcome="completed"))
        logger.info(f"[guidance] ✓ Guidance stopped for: {task}")
        return (
            f"Guidance stopped for: {task}. "
            "Acknowledge briefly — 'No problem' or 'You're all set'. Keep it short."
        )

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
                max_tokens=30,
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
                                f"{question}. "
                                "Answer in 1-5 words. Name the thing, read labels. Nothing else."
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

def _classify_task_type(text: str) -> str:
    """Classify the task type from user speech. Returns empty string if unclear.
    Uses string matching — no LLM call, runs on every first meaningful turn."""
    t = text.lower()
    if any(w in t for w in ["replac", "install", "putting in", "swap", "hooking up", "hook up", "adding a", "add a"]):
        return "install"
    if any(w in t for w in ["troubleshoot", "diagnos", "not working", "won't work", "broken", "doesn't work", "why is", "won't start", "won't turn"]):
        return "diagnostic"
    if any(w in t for w in ["repair", "fixing", "fix ", "patch", "leak", "leaking"]):
        return "repair"
    if any(w in t for w in ["inspect", "check if", "test ", "is this", "does this look", "look at"]):
        return "inspect"
    if any(w in t for w in ["maintain", "service ", "clean ", "flush", "filter change"]):
        return "maintenance"
    return ""


async def _classify_environment(frame_b64: str, agent: "ArrivalAgent"):
    """One-time environment classification from the first good frame.
    Runs once per session — result stored on agent and pushed to Supabase session row."""
    if agent._environment_classified:
        return
    agent._environment_classified = True  # Prevent concurrent/duplicate calls
    try:
        client = _get_anthropic_client()
        response = await asyncio.wait_for(
            client.messages.create(
                model=config.ANTHROPIC_VISION_MODEL,
                max_tokens=80,
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
                                'Classify this work site. JSON only:\n'
                                '{"indoor_outdoor":"indoor|outdoor","setting":"residential|commercial|industrial",'
                                '"space":"attic|crawlspace|basement|electrical_panel|rooftop|mechanical_room|wall_cavity|outdoor_equipment|garage|utility_room|other"}'
                            ),
                        },
                    ],
                }],
            ),
            timeout=8.0,
        )
        result = response.content[0].text.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if result.startswith("{"):
            import json as _json
            data = _json.loads(result)
            agent._environment_type = data.get("indoor_outdoor", "")
            agent._environment_setting = data.get("setting", "")
            agent._environment_space = data.get("space", "")
            logger.info(f"[label] Environment: {agent._environment_type}/{agent._environment_setting}/{agent._environment_space}")
            # Push to Supabase session row
            if getattr(agent, '_spatial_recorder', None) and agent._spatial_recorder._session_id:
                asyncio.ensure_future(
                    agent._spatial_recorder.update_environment(
                        agent._environment_type, agent._environment_setting, agent._environment_space
                    )
                )
    except Exception as e:
        logger.debug(f"[label] Environment classification failed: {e}")
        agent._environment_classified = False  # Allow retry on next frame


async def _run_video_track(track: rtc.Track, agent: "ArrivalAgent"):
    """Process frames from a subscribed LiveKit video track.
    Extracted to module level so it can be called from on_track_subscribed AND
    the existing-track scan after session.start()."""
    video_stream = rtc.VideoStream(track)
    frame_count = 0
    last_hash = ""
    logger.info(f"[video] ★ Starting video stream processor for track {track.sid}")
    async for frame_event in video_stream:
        frame_count += 1
        # Process every 10th frame (~1fps if source is 10fps, ~3fps at 30fps)
        if frame_count % 10 != 0:
            continue
        try:
            argb_frame = frame_event.frame.convert(rtc.VideoBufferType.RGBA)
            jpg_bytes = _frame_to_jpeg(argb_frame)
            if jpg_bytes:
                import base64 as _b64
                b64 = _b64.b64encode(jpg_bytes).decode('ascii')
                new_hash = b64[-20:]
                changed = new_hash != last_hash
                last_hash = new_hash
                agent._latest_frame = b64
                agent._frame_received_at = time.time()
                if frame_count <= 30 or frame_count % 100 == 0 or changed:
                    logger.info(f"[video] Frame #{frame_count} ({len(b64)//1024}KB) changed={changed}")
                # Trigger one-time environment classification on first frame
                if not agent._environment_classified:
                    asyncio.ensure_future(_classify_environment(b64, agent))
        except Exception as e:
            if frame_count <= 10:
                logger.warning(f"[video] Frame conversion failed: {e}")


def _extract_task_from_speech(text: str) -> str:
    """Extract a task description from user speech. Returns empty string if no task found."""
    text_lower = text.lower().strip()
    for phrase in _TASK_PHRASES:
        idx = text_lower.find(phrase)
        if idx >= 0:
            # Extract the phrase + the rest of the sentence (up to 80 chars)
            task = text[idx:idx + 80].strip()
            # Trim at sentence end
            for end in (".", "!", "?", ",", " so ", " and ", " but "):
                pos = task.find(end, len(phrase))
                if pos > 0:
                    task = task[:pos].strip()
                    break
            if len(task) > len(phrase) + 2:  # Must have substance beyond the phrase
                return task
    return ""


def _has_task_context(agent: "ArrivalAgent") -> bool:
    """Check if we have any understanding of what the worker is doing."""
    if agent._guidance_active:
        return True
    if agent._inferred_task and (time.time() - agent._inferred_task_updated_at) < TASK_CONTEXT_DECAY_SECONDS:
        return True
    if agent._equipment_type or agent._equipment_brand:
        return True
    return False


async def _analyze_scene(frame_b64: str, agent: "ArrivalAgent") -> Optional[dict]:
    """
    Unified scene analysis — perception + decision in ONE API call.
    Returns dict with: {"objects": [...], "activity": "...", "stage": "...", "speak": "..." or null}
    Or None on failure.
    """
    client = _get_anthropic_client()
    scene = agent._scene

    # Build context based on what we know
    task_context = ""
    if agent._guidance_active:
        task_context = f"TASK: {agent._guidance_task}\n"
        if agent._guidance_brief:
            # Full brief — guidance needs all context to track task progression
            task_context += f"JOB KNOWLEDGE:\n{agent._guidance_brief}\n"
    elif agent._inferred_task:
        task_context = f"TASK: {agent._inferred_task}\n"

    equip = agent._equipment_context_str()
    if equip:
        task_context += f"EQUIPMENT: {equip}\n"

    # What we already know about the scene
    scene_so_far = ""
    if scene.activity or scene.objects:
        parts = []
        if scene.activity:
            parts.append(f"Activity: {scene.activity}")
        if scene.objects:
            parts.append(f"Objects: {', '.join(scene.objects[:8])}")
        if scene.stage:
            parts.append(f"Stage: {scene.stage}")
        scene_so_far = "SCENE SO FAR: " + ". ".join(parts) + "\n"

    # What we already said (anti-repeat)
    already_said = ""
    if scene.observations_made:
        already_said = f"ALREADY SAID (do NOT repeat): {'; '.join(scene.observations_made[-5:])}\n"

    # Confidence context — if we've been ignored, be more selective
    confidence_note = ""
    if scene.ignored_count >= 2:
        confidence_note = "You've been ignored recently. Only speak for SAFETY issues.\n"
    elif scene.ignored_count >= 1:
        confidence_note = "Your last comment was ignored. Be extra selective about speaking.\n"

    if agent._guidance_active:
        # GUIDANCE MODE — actively guide them through the job
        prompt = (
            "You're guiding a trade worker through a job. You're watching through their phone camera.\n\n"
            f"{task_context}"
            f"{scene_so_far}"
            f"{already_said}"
            f"{confidence_note}\n"
            "Respond in JSON only:\n"
            '{"objects": ["item1", "item2"], "activity": "what they are doing", "stage": "prep|execution|testing|cleanup", "speak": "what to tell them" or null}\n\n'
            "You are ACTIVELY GUIDING. Your job is to:\n"
            "1. Watch what they're doing and figure out where they are in the job\n"
            "2. When they finish a step or pause, tell them what to do next\n"
            "3. If they're doing something wrong or about to make a mistake, speak up immediately\n"
            "4. If they're in the middle of doing something correctly, stay quiet and let them work\n\n"
            "WHEN TO SPEAK:\n"
            "- They just finished something → tell them what's next\n"
            "- They paused or look stuck → tell them what to do\n"
            "- They're about to make a mistake → warn them\n"
            "- Safety issue → alert immediately\n\n"
            "WHEN TO STAY QUIET (speak = null):\n"
            "- They're actively working and doing it right → let them work\n"
            "- You just told them something and they're doing it → wait\n"
            "- You can't clearly see what's happening → don't guess\n"
            "- You already said this exact thing\n\n"
            "SPEAK STYLE: Short, direct, like a vet standing next to them. Under 20 words.\n"
            "Examples: 'Good, now connect the black to the brass screw.' | 'Hold up — kill the breaker first.' | "
            "'That's your neutral, white wire goes to silver.'\n"
            "JSON only, no other text."
        )
    else:
        # PASSIVE MODE — only speak for clear safety/error issues
        prompt = (
            "You're watching a trade worker through their phone camera. The phone may be propped up "
            "far away or at an angle. Objects may be small, blurry, or partially hidden.\n\n"
            f"{task_context}"
            f"{scene_so_far}"
            f"{already_said}"
            f"{confidence_note}\n"
            "Respond in JSON only:\n"
            '{"objects": ["item1", "item2"], "activity": "what they are doing", "stage": "prep|execution|testing|cleanup", "speak": null}\n\n'
            "ACCURACY IS EVERYTHING. You must be RIGHT or SILENT. Never guess.\n\n"
            "For objects: only list what you can clearly identify. If you can see it's a wrench but not "
            "what type, say 'wrench'. If you can see wire but not the gauge, say 'wire'. Don't guess specifics "
            "you can't actually read or measure from the image.\n\n"
            "SPEAK RULES (speak = null is the default — silence is almost always correct):\n"
            "- SAFETY: you can CLEARLY see exposed live wires, gas leak, active fire, fall risk → speak\n"
            "- WRONG PART: you can CLEARLY read or identify the wrong gauge, wrong fitting, wrong size → speak\n"
            "- MISTAKE: you can CLEARLY see them about to connect wrong terminal, wrong pipe, reversed polarity → speak\n"
            "- EVERYTHING ELSE → null. If you're 80% sure, that's not sure enough. Stay quiet.\n\n"
            "NEVER speak about:\n"
            "- What you see (no narrating the scene)\n"
            "- Image quality, blur, angles, lighting\n"
            "- Things you THINK you see but aren't certain\n"
            "- General safety reminders they already know\n"
            "- Anything you already said\n"
            "- Recommendations or tips they didn't ask for\n\n"
            "If you speak: under 12 words, like a coworker. One thing only.\n"
            "Example: 'Hey — that's 14 gauge, you need 12 for 20 amp.'\n"
            "JSON only, no other text."
        )

    try:
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
                        {"type": "text", "text": prompt},
                    ],
                }],
            ),
            timeout=12.0,
        )
        result = response.content[0].text.strip()

        # Parse JSON — handle common issues (markdown fences, etc.)
        json_str = result
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if json_str.startswith("{"):
            import json as json_mod
            parsed = json_mod.loads(json_str)
            return parsed
        else:
            logger.debug(f"[scene] Non-JSON response: {result[:100]}")
            return None

    except Exception as e:
        logger.debug(f"[scene] Analysis failed: {e}")
        return None


async def proactive_monitor(agent: ArrivalAgent, session: AgentSession):
    """Background task: intelligent proactive vision monitor.

    Phase 1: Frame diff (FREE) — skip if scene unchanged
    Phase 2: Scene analysis (ONE Sonnet call) — perception + decision together
    Adaptive intervals: faster when scene changes, slower when static.
    """
    logger.info("[proactive] Monitor started — waiting for greeting to finish...")
    await asyncio.sleep(6)

    scene = agent._scene
    consecutive_unchanged = 0
    api_calls_this_session = 0

    while True:
        try:
            # Adaptive interval based on mode and scene state
            if agent._guidance_active:
                # Guidance mode — check frequently, user expects active guiding
                if consecutive_unchanged > 5:
                    interval = 20  # Scene static during guidance — maybe they're working
                else:
                    interval = GUIDANCE_CHECK_INTERVAL  # 8s — actively watching
            elif consecutive_unchanged > 8:
                interval = SCENE_STATIC_BACKOFF  # 60s — camera is clearly static
            elif consecutive_unchanged > 3:
                interval = 30  # Slowing down — not much happening
            elif scene.ignored_count >= 2:
                interval = SCENE_IGNORED_BACKOFF  # 45s — user is ignoring us
            else:
                interval = SCENE_ACTIVE_INTERVAL if _has_task_context(agent) else SCENE_POLL_INTERVAL

            await asyncio.sleep(interval)

            # Check outcome inference + outcome prompting for spatial data
            if getattr(agent, '_spatial_recorder', None):
                try:
                    await agent._spatial_recorder.check_outcome_inference()
                    # After a sequence ends, ask the user if it worked
                    if agent._spatial_recorder.should_prompt_outcome():
                        await session.generate_reply(
                            instructions="Casually ask if that fixed it. One short sentence like 'That sort it out?' or 'All good?' — don't make it sound like a survey."
                        )
                except Exception:
                    pass

            if not agent._proactive_enabled or not agent._room_name:
                continue

            now = time.time()

            # Muted by user
            if now < agent._proactive_muted_until:
                continue

            # Task context decay
            if agent._inferred_task and (now - agent._inferred_task_updated_at) > TASK_CONTEXT_DECAY_SECONDS:
                logger.info(f"[proactive] Task context expired: '{agent._inferred_task[:40]}'")
                agent._inferred_task = ""

            # --- Phase 1: Get frame + diff (FREE) ---
            frame = None
            if agent._latest_frame and (now - agent._frame_received_at) < 4:
                frame = agent._latest_frame
            if not frame:
                frame = get_frame(agent._room_name)
            if not frame:
                continue

            # Frame diff — skip API call if scene hasn't changed meaningfully
            if not agent._frame_changed(frame):
                consecutive_unchanged += 1
                scene.frames_since_change += 1
                continue

            # Scene changed — reset counter, update hash
            scene.last_scene_hash = agent._frame_hash(frame)
            consecutive_unchanged = 0

            # Track if user ignored our last interjection
            # (we spoke, 15+ seconds passed, user didn't talk)
            if scene.last_spoken_time > 0 and not scene.user_responded_after_speak:
                if (now - scene.last_spoken_time) > 15 and (agent._last_user_speech_time < scene.last_spoken_time):
                    scene.ignored_count += 1
                    logger.debug(f"[proactive] User ignored us (count={scene.ignored_count})")

            # --- Phase 2: Analyze scene (ONE Sonnet call) ---
            # Skip if user just spoke — their query's LLM call is more urgent,
            # and concurrent proactive calls cause Anthropic queue latency.
            if (now - agent._last_user_speech_time) < 12:
                logger.debug("[proactive] Skipping API call — user spoke recently, prioritizing reply")
                continue

            try:
                result = await _analyze_scene(frame, agent)
                api_calls_this_session += 1
            except Exception as e:
                logger.debug(f"[proactive] Analysis failed: {e}")
                continue

            if not result:
                continue

            # Update scene memory from perception
            objects = result.get("objects", [])
            activity = result.get("activity", "")
            stage = result.get("stage", "")
            speak = result.get("speak")

            scene.update_from_analysis(objects, activity, stage)

            if objects or activity:
                logger.info(f"[scene] Objects: {objects[:5]} | Activity: {activity} | Stage: {stage} (API call #{api_calls_this_session})")

            # --- Decision: should we speak? ---
            if not speak or speak == "null" or speak.upper() in ("NULL", "NONE", "QUIET", "NOTHING"):
                continue

            # ============================================================
            # ENGINEERING GATES — model output must pass ALL of these
            # These are hard rules, not prompts. Model can say whatever
            # it wants — these gates decide if it actually reaches TTS.
            #
            # GUIDANCE MODE: gates are relaxed because the user ASKED
            # for help. Guidance interjections are expected and welcome.
            # PASSIVE MODE: gates are strict — only speak when certain.
            # ============================================================

            speak_lower = speak.lower()
            is_guidance = agent._guidance_active

            # Gate 1: Too long = not confident (passive) or rambling (guidance)
            max_len = 200 if is_guidance else 80
            if len(speak) > max_len:
                logger.debug(f"[proactive] GATE: too long ({len(speak)} chars), dropping: {speak[:50]}")
                continue

            # Gate 2: Hedging = not sure = don't speak (both modes)
            _HEDGE_WORDS = {"might", "maybe", "possibly", "could be", "looks like it might",
                            "not sure", "hard to tell", "it's possible", "potentially"}
            if any(hedge in speak_lower for hedge in _HEDGE_WORDS):
                logger.debug(f"[proactive] GATE: hedging detected, dropping: {speak[:50]}")
                continue

            # Gate 3: Narrating = useless (passive only — guidance can reference what it sees)
            if not is_guidance:
                _NARRATION = {"i can see", "i see", "you're looking at", "the camera shows",
                              "in the frame", "in the image", "there is a",
                              "there are", "i notice", "i can make out"}
                if any(narr in speak_lower for narr in _NARRATION):
                    logger.debug(f"[proactive] GATE: narration detected, dropping: {speak[:50]}")
                    continue

            # Gate 4: Generic advice (passive only — guidance can direct actions)
            if not is_guidance:
                _GENERIC = {"be careful", "stay safe", "make sure to", "don't forget to",
                            "remember to", "you should", "it's important to",
                            "keep in mind", "just a reminder"}
                if any(gen in speak_lower for gen in _GENERIC):
                    logger.debug(f"[proactive] GATE: generic advice, dropping: {speak[:50]}")
                    continue

            # Gate 5: Must reference detected objects (passive only)
            # Guidance can talk about the task without naming visible objects
            # Uses word-level matching — "copper wire" matches if "wire" appears in speak
            if not is_guidance:
                if objects:
                    obj_words = set()
                    for obj in objects:
                        for word in obj.lower().split():
                            if len(word) > 2:  # Skip tiny words like "a", "of"
                                obj_words.add(word)
                    speak_words = set(speak_lower.split())
                    has_obj_ref = bool(obj_words & speak_words)  # intersection

                    if not has_obj_ref:
                        safety_keywords = {"danger", "exposed", "live", "wire", "gas", "leak", "fire", "shock",
                                           "breaker", "shut", "stop", "disconnect",
                                           "ppe", "goggles", "gloves", "harness"}
                        if not (safety_keywords & speak_words):
                            logger.debug(f"[proactive] GATE: speak doesn't reference detected objects, dropping: {speak[:50]}")
                            continue

            # Anti-repeat check
            if scene.already_said(speak):
                logger.debug(f"[proactive] Skipping repeat: {speak[:50]}")
                continue

            # Cooldown — don't spam (guidance gets shorter cooldown — user expects active guiding)
            cooldown = GUIDANCE_SPEAK_COOLDOWN if is_guidance else SCENE_POST_SPEAK_COOLDOWN
            if (now - scene.last_spoken_time) < cooldown:
                logger.debug(f"[proactive] Cooldown active ({cooldown}s), skipping: {speak[:50]}")
                continue

            # Don't interrupt active conversation
            if (now - agent._last_user_speech_time) < 5:
                continue

            # Pushback check — user has explicitly told us to shut up
            if agent._user_pushback_count > 2 and (now - scene.last_spoken_time) < 60:
                continue

            # --- All gates passed — speak ---
            safety_keywords = {"danger", "exposed", "live wire", "gas leak", "fire", "shock",
                               "kill the breaker", "shut off", "stop", "careful", "disconnect",
                               "ppe", "goggles", "gloves", "harness"}
            is_safety = any(kw in speak_lower for kw in safety_keywords)

            if is_safety:
                instruction = f"STOP — {speak}. Alert them immediately."
                trigger_type = "safety_alert"
            else:
                instruction = speak
                trigger_type = "contextual_alert"

            logger.info(f"[proactive] ★ {'SAFETY' if is_safety else 'SPEAK'}: {speak}")
            await session.generate_reply(instructions=instruction)

            # Record in scene memory + reset ignored tracking
            scene.record_speech(speak)
            scene.user_responded_after_speak = False  # Will be set to True when user talks

            # Spatial recording
            if getattr(agent, '_spatial_recorder', None):
                asyncio.ensure_future(agent._spatial_recorder.trigger_recording(
                    trigger_type=trigger_type, trigger_text=speak, agent=agent,
                    monitor_state='GUIDED' if agent._guidance_active else 'ACTIVE'))

        except asyncio.CancelledError:
            logger.info(f"[proactive] Monitor stopped. Total API calls: {api_calls_this_session}")
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
            "text": "[Camera feed]",
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
        team_id = None
        active_job = None

        for participant in ctx.room.remote_participants.values():
            if participant.metadata:
                try:
                    meta = json.loads(participant.metadata)
                    user_id = meta.get("user_id", user_id)
                    mode = meta.get("mode", mode)
                    team_id = meta.get("team_id")
                    active_job = meta.get("active_job")  # job/residence name
                except (json.JSONDecodeError, TypeError):
                    pass
                break

        logger.info(f"[arrival-agent] Room={room_name} user={user_id} mode={mode} team={team_id or 'none'} job={active_job or 'none'}")

        # Select prompt based on mode — append VOICE_KNOWLEDGE for brand/diagnostic depth
        prompt = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE

        # Inject active job context so agent always knows which job/residence it's on
        if active_job:
            prompt += (
                f"\n\nACTIVE JOB: {active_job}\n"
                f"You are currently on the {active_job} job. When answering questions about specs, "
                f"measurements, plans, or materials — reference the {active_job} documents first. "
                f"The user does not need to tell you which job they're on — you already know."
            )

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
                model=config.ANTHROPIC_VISION_MODEL,  # Sonnet for accurate vision
                api_key=config.ANTHROPIC_API_KEY,
                max_tokens=400,
                caching="ephemeral",  # Cache system prompt — 90% cheaper on input tokens
            ),
            tts=elevenlabs.TTS(
                voice_id=config.ELEVENLABS_JOB_VOICE_ID if mode == "job" else (config.ELEVENLABS_VOICE_ID or config.ELEVENLABS_JOB_VOICE_ID),
                model="eleven_flash_v2_5",
                api_key=config.ELEVENLABS_API_KEY,
                encoding="pcm_24000",
                voice_settings=elevenlabs.VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    use_speaker_boost=True,
                ),
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

        # Set room name, room reference, and user context
        agent._room_name = room_name
        agent._room = ctx.room
        agent._user_id = user_id
        agent._team_id = team_id
        agent._active_job = active_job

        # --- Spatial Intelligence Recorder ---
        recording_consent = False
        for participant in ctx.room.remote_participants.values():
            if participant.metadata:
                try:
                    meta = json.loads(participant.metadata)
                    recording_consent = meta.get("recording_consent", False)
                except (json.JSONDecodeError, TypeError):
                    pass
                break

        try:
            from app.services.spatial_recorder import SpatialRecorder
            spatial_recorder = SpatialRecorder()
            await spatial_recorder.start_session(
                room_name=room_name,
                user_id=user_id,
                team_id=team_id,
                trade=None,  # TODO: pass trade from profile when available in metadata
                equipment=None,  # Updated later via data channel equipment_context
                consent=recording_consent,
            )
            agent._spatial_recorder = spatial_recorder
            logger.info(f"[arrival-agent] Spatial recorder initialized (consent={recording_consent})")
        except Exception as e:
            logger.warning(f"[arrival-agent] Spatial recorder init failed (non-fatal): {e}")
            agent._spatial_recorder = None

        # Fetch user's uploaded documents and inject into prompt so AI knows what's available
        try:
            from app.services.supabase import list_documents
            docs = await list_documents(user_id, team_id=team_id)
            if docs:
                doc_names = [d.get("filename", "") for d in docs if d.get("filename")]
                if doc_names:
                    doc_list = ", ".join(doc_names[:20])
                    doc_inject = (
                        f"\n\nUPLOADED DOCUMENTS: The user has these documents stored in the system: {doc_list}. "
                        f"These are TEXT documents (PDFs, plans, manuals) — NOT things on the camera. "
                        f"When asked about any of them, their content is automatically injected as [UPLOADED JOB DOCS] context in your messages. "
                        f"NEVER say you can't see the plans or ask the user to show them on screen — "
                        f"just read the [UPLOADED JOB DOCS] context and answer from it."
                    )
                    prompt = prompt + doc_inject
                    asyncio.ensure_future(agent.update_instructions(prompt))
                    logger.info(f"[arrival-agent] Injected {len(doc_names)} document names into prompt")
        except Exception as e:
            logger.debug(f"[arrival-agent] Doc list fetch failed (non-fatal): {e}")

        await session.start(agent=agent, room=ctx.room)
        logger.info("[arrival-agent] ✓ Session started — voice pipeline active")

        # Listen for data channel messages from mobile app
        @ctx.room.on("data_received")
        def on_data(data_packet):
            try:
                raw = data_packet.data
                logger.info(f"[data-channel] Received {len(raw)} bytes, type={type(raw).__name__}")
                payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                msg_type = payload.get("type", "")
                logger.info(f"[data-channel] Message type: {msg_type}")

                if msg_type == "camera_frame" and payload.get("image"):
                    agent.update_camera_frame(payload["image"])

                elif msg_type == "equipment_context":
                    # Frontend sends equipment info when user selects equipment type
                    agent._equipment_type = payload.get("equipment_type", "")
                    agent._equipment_brand = payload.get("brand", "")
                    agent._equipment_model = payload.get("model", "")
                    eq_str = agent._equipment_context_str()
                    if eq_str:
                        logger.info(f"[arrival-agent] Equipment context updated: {eq_str}")

                elif msg_type == "guidance_state_restore":
                    # Frontend sends cached guidance state on reconnect
                    state = payload.get("state", {})
                    if state and not agent._guidance_active:
                        agent.restore_guidance_state(state)

                elif msg_type == "guidance_state_request":
                    # Frontend asks for current guidance state (on reconnect)
                    try:
                        state_msg = json.dumps({
                            "type": "guidance_state",
                            "state": agent.get_guidance_state(),
                        })
                        for p in ctx.room.remote_participants.values():
                            asyncio.ensure_future(
                                ctx.room.local_participant.publish_data(
                                    state_msg.encode("utf-8"),
                                    reliable=True,
                                )
                            )
                            break
                    except Exception as e:
                        logger.debug(f"[guidance] State broadcast failed: {e}")

                elif msg_type == "guidance_request":
                    # User tapped "Guide me" button — interrupt current speech
                    # and ask them what they need help with
                    logger.info("[guidance] User tapped Guide me button")
                    asyncio.ensure_future(session.generate_reply(
                        instructions=(
                            "The tech just tapped the 'Guide me' button — they want step-by-step guidance. "
                            "Ask them naturally what they're working on or need help with. "
                            "Keep it short and warm, like: 'Sure! What are you working on?' "
                            "Once they tell you, call start_guidance with their task."
                        )
                    ))

                elif msg_type == "guidance_stop":
                    # User tapped "Stop guidance" button
                    if agent._guidance_active:
                        task = agent._guidance_task
                        agent._guidance_active = False
                        agent._guidance_task = ""
                        agent._guidance_brief = ""
                        agent._guidance_context = ""
                        # Spatial recorder cleanup
                        if getattr(agent, '_spatial_recorder', None) and agent._spatial_recorder._current_sequence_id:
                            asyncio.ensure_future(agent._spatial_recorder._compare_sequence_frames(agent))
                            asyncio.ensure_future(agent._spatial_recorder.end_sequence(outcome="completed"))
                        # Reset prompt
                        asyncio.ensure_future(agent.update_instructions((JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE))
                        agent._has_injected_codes = False
                        logger.info(f"[guidance] User stopped guidance for: {task}")
                        asyncio.ensure_future(session.generate_reply(
                            instructions=f"Tech stopped guidance for: {task}. Say 'No problem, I'm here if you need me.'"
                        ))
                    else:
                        logger.debug("[guidance] Stop received but no guidance active")

            except Exception as e:
                logger.warning(f"[data-channel] Error handling data: {type(e).__name__}: {e}")

        logger.info("[arrival-agent] ✓ Data channel listener registered")

        # ---------------------------------------------------------------
        # Text stream handler — fallback for data channel (which is broken
        # in production with LiveKit client v2.17+ / agents v1.4)
        # The frontend can send JSON commands via text streams as well.
        # ---------------------------------------------------------------
        def _handle_text_stream(reader, participant_identity: str):
            async def _process():
                try:
                    full_text = ""
                    async for chunk in reader:
                        full_text += chunk
                    logger.info(f"[text-stream] Received from {participant_identity}: {full_text[:100]}")
                    payload = json.loads(full_text)
                    msg_type = payload.get("type", "")

                    if msg_type == "guidance_request":
                        logger.info("[text-stream] Guidance request received")
                        await session.generate_reply(
                            instructions=(
                                "The tech just tapped the 'Guide me' button — they want step-by-step guidance. "
                                "Ask them naturally what they're working on or need help with. "
                                "Keep it short: 'Sure! What are you working on?' "
                                "Once they tell you, call start_guidance with their task."
                            )
                        )
                    elif msg_type == "guidance_stop":
                        if agent._guidance_active:
                            task = agent._guidance_task
                            agent._guidance_active = False
                            agent._guidance_task = ""
                            agent._guidance_brief = ""
                            agent._guidance_context = ""
                            # Spatial recorder cleanup
                            if getattr(agent, '_spatial_recorder', None) and agent._spatial_recorder._current_sequence_id:
                                asyncio.ensure_future(agent._spatial_recorder._compare_sequence_frames(agent))
                                asyncio.ensure_future(agent._spatial_recorder.end_sequence(outcome="completed"))
                            asyncio.ensure_future(agent.update_instructions(
                                (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                            ))
                            agent._has_injected_codes = False
                            logger.info(f"[text-stream] User stopped guidance for: {task}")
                            await session.generate_reply(
                                instructions=f"Tech stopped guidance for: {task}. Say 'No problem, I'm here if you need me.'"
                            )
                    elif msg_type == "equipment_context":
                        agent._equipment_type = payload.get("equipment_type", "")
                        agent._equipment_brand = payload.get("brand", "")
                        agent._equipment_model = payload.get("model", "")
                        logger.info(f"[text-stream] Equipment context: {agent._equipment_context_str()}")
                    elif msg_type == "camera_frame" and payload.get("image"):
                        agent.update_camera_frame(payload["image"])
                except Exception as e:
                    logger.warning(f"[text-stream] Error: {e}")

            asyncio.ensure_future(_process())

        try:
            ctx.room.register_text_stream_handler("arrival-commands", _handle_text_stream)
            logger.info("[arrival-agent] ✓ Text stream handler registered (topic: arrival-commands)")
        except Exception as e:
            logger.warning(f"[arrival-agent] Text stream handler registration failed: {e}")

        # ---------------------------------------------------------------
        # Video track subscriber — grab frames from LiveKit video track
        # This bypasses expo-camera entirely. The frontend publishes its
        # camera as a LiveKit video track, and we grab frames here.
        #
        # IMPORTANT: handler registered here so it catches future tracks.
        # We also scan existing tracks below in case the client published
        # before this handler was registered.
        # ---------------------------------------------------------------
        @ctx.room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            logger.info(f"[video] Track subscribed: kind={track.kind}, from={participant.identity}")
            if track.kind != rtc.TrackKind.KIND_VIDEO:
                return
            logger.info(f"[video] ★★★ VIDEO TRACK from {participant.identity} — starting processor ★★★")
            asyncio.ensure_future(_run_video_track(track, agent))

        # Scan existing subscribed tracks — event may have fired before handler registered
        _existing_video = 0
        for _p in ctx.room.remote_participants.values():
            for _pub in _p.track_publications.values():
                if _pub.track and _pub.track.kind == rtc.TrackKind.KIND_VIDEO:
                    logger.info(f"[video] ★ Existing video track found from {_p.identity} — processing")
                    asyncio.ensure_future(_run_video_track(_pub.track, agent))
                    _existing_video += 1
        if _existing_video == 0:
            logger.info("[video] No existing video tracks — waiting for track_subscribed event")

        # Track user speech for proactive monitor + engagement + mute detection
        # Only match mute/pushback when the ENTIRE utterance matches exactly
        # to avoid false positives (e.g., "stop valve testing" should NOT trigger)
        _MUTE_PHRASES = {
            "stop", "stop talking", "be quiet", "shut up", "mute", "quiet",
            "hush", "enough", "stop it", "that's enough", "ok stop", "okay stop",
        }
        _PUSHBACK_PHRASES = {"it's fine", "that's fine", "not an issue", "i know", "already know", "don't worry"}
        _GUIDANCE_EXIT_PHRASES = {
            "i got it", "i got it from here", "got it from here", "i'll take it from here",
            "stop guiding", "stop guiding me", "end guidance", "that's enough guidance",
            "i can take it from here", "i know the rest", "i'm good", "im good",
        }
        _GUIDANCE_ADVANCE_PHRASES = {
            "done", "next", "next step", "what's next", "whats next", "ok done",
            "okay done", "got it", "finished", "move on", "ok next", "okay next",
        }
        # Guidance start phrases — when user wants step-by-step guidance via voice
        _GUIDANCE_START_PHRASES = {
            "guide me", "walk me through", "help me step by step",
            "can you guide me", "can you walk me through",
        }

        @session.on("user_input_transcribed")
        def on_user_speech(ev):
            agent._last_user_speech_time = time.time()
            transcript = getattr(ev, "text", "") or getattr(ev, "transcript", "") or ""
            if not transcript:
                return
            if not getattr(ev, 'is_final', True):
                return

            text_lower = transcript.lower().strip()

            # Store conversation context (for proactive analyzer) — 10 messages = 5 turns
            agent._conversation_context.append({"role": "user", "content": transcript})
            if len(agent._conversation_context) > 10:
                agent._conversation_context.pop(0)

            # Outcome detection — if a sequence just ended and user responds
            if getattr(agent, '_spatial_recorder', None) and agent._spatial_recorder._pending_outcome_sequence_id:
                _YES_WORDS = {"yes", "yeah", "yep", "yup", "fixed", "sorted", "works", "working", "perfect"}
                _NO_WORDS = {"no", "nope", "nah", "still"}
                words = set(text_lower.split())
                if words & _YES_WORDS or "all good" in text_lower or "that's it" in text_lower:
                    asyncio.ensure_future(agent._spatial_recorder.set_outcome("fixed"))
                elif words & _NO_WORDS or "still broken" in text_lower or "didn't work" in text_lower or "not working" in text_lower or "same issue" in text_lower:
                    asyncio.ensure_future(agent._spatial_recorder.set_outcome("not_fixed"))

            # Extract task context for proactive vision grounding
            task = _extract_task_from_speech(transcript)
            if task:
                agent._inferred_task = task
                agent._inferred_task_updated_at = time.time()
                logger.info(f"[proactive] Task inferred from speech: '{task}'")

            # Task type classification — runs once on first meaningful turn (≥3 words)
            if not agent._task_type_classified and len(text_lower.split()) >= 3:
                task_type = _classify_task_type(transcript)
                if task_type:
                    agent._task_type = task_type
                    agent._task_type_classified = True
                    logger.info(f"[label] Task type classified: {task_type}")
                    if getattr(agent, '_spatial_recorder', None) and agent._spatial_recorder._session_id:
                        asyncio.ensure_future(agent._spatial_recorder.update_task_type(task_type))

            # Pre-inject error code data so LLM has it without needing a tool call.
            # lookup_error_code is a fast dict lookup — no async/network needed.
            # NOTE: We build the base prompt once and layer injections on top.
            # Error code injection and guidance injection are ADDITIVE, not exclusive.
            error_result = lookup_error_code(transcript)
            error_inject = ""
            if error_result:
                code_context = format_error_code_context(error_result)
                error_inject = f"\n\n## VERIFIED ERROR CODE — USE THIS EXACTLY:\n{code_context}"
                agent._has_injected_codes = True
                logger.info(f"[arrival-agent] ★ Pre-injected error code for: {transcript[:50]}")
            elif agent._has_injected_codes:
                agent._has_injected_codes = False

            # Detect guidance exit — user wants to stop guided procedure
            if agent._guidance_active and text_lower in _GUIDANCE_EXIT_PHRASES:
                task = agent._guidance_task
                agent._guidance_active = False
                agent._guidance_task = ""
                agent._guidance_brief = ""
                agent._guidance_context = ""
                # Spatial recorder cleanup
                if getattr(agent, '_spatial_recorder', None) and agent._spatial_recorder._current_sequence_id:
                    asyncio.ensure_future(agent._spatial_recorder._compare_sequence_frames(agent))
                    asyncio.ensure_future(agent._spatial_recorder.end_sequence(outcome="completed"))
                # Reset prompt to clean state
                asyncio.ensure_future(agent.update_instructions((JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE))
                agent._has_injected_codes = False
                logger.info(f"[guidance] User exited guidance for: {task}")
                asyncio.ensure_future(session.generate_reply(
                    instructions=f"Tech said '{transcript}' to end guidance for: {task}. Say something like 'You got it!' or 'Holler if you need me.' Brief."
                ))
                return

            # Inject guidance context + error code context into prompt (merged, not exclusive)
            if agent._guidance_active and agent._guidance_brief:
                base = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                guidance_inject = (
                    f"\n\n## REAL-TIME GUIDANCE ACTIVE\n"
                    f"Task: {agent._guidance_task}\n\n"
                    f"YOUR KNOWLEDGE OF THIS JOB:\n{agent._guidance_brief}\n\n"
                    "You know this job inside out. Guide them naturally based on what you see "
                    "on camera. Tell them what to do next when they're ready. "
                    "NEVER use numbered lists or steps. Just talk like a vet would."
                )
                # Merge: guidance + error code (if user asked about a code mid-guidance)
                asyncio.ensure_future(agent.update_instructions(base + guidance_inject + error_inject))
            else:
                # No guidance active — just base + error codes (if any)
                base = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                asyncio.ensure_future(agent.update_instructions(base + error_inject))

            # Detect mute commands — entire utterance must exactly match a mute phrase
            # to avoid false positives like "stop valve testing" or "that's quiet today"
            if text_lower in _MUTE_PHRASES:
                agent._proactive_muted_until = time.time() + PROACTIVE_MUTE_DURATION
                logger.info(f"[proactive] Muted for {PROACTIVE_MUTE_DURATION}s — user said: '{text_lower}'")
                return

            # Detect pushback — only on short utterances (< 8 words)
            word_count = len(text_lower.split())
            if word_count <= 7 and any(phrase in text_lower for phrase in _PUSHBACK_PHRASES):
                agent._user_pushback_count += 1
                logger.info(f"[proactive] Pushback #{agent._user_pushback_count} — user said: '{text_lower}'")
                return

        # Track assistant responses for conversation context
        @session.on("conversation_item_added")
        def on_conversation_item(ev):
            item = getattr(ev, 'item', None)
            if item and getattr(item, 'role', '') == 'assistant':
                text = ""
                if hasattr(item, 'content') and isinstance(item.content, list):
                    text = " ".join(c.text for c in item.content if hasattr(c, 'text'))
                elif hasattr(item, 'text'):
                    text = item.text
                if text:
                    agent._conversation_context.append({"role": "assistant", "content": text})
                    if len(agent._conversation_context) > 10:
                        agent._conversation_context.pop(0)

        # Background task: keep injecting latest frame into agent context
        _frame_injector_count = [0]  # mutable counter in closure

        async def frame_injector():
            """Poll HTTP frame store every 2s — keeps _latest_frame fresh for on_user_turn_completed."""
            while True:
                try:
                    await asyncio.sleep(2)
                    frame = await agent.get_current_frame()
                    _frame_injector_count[0] += 1
                    if frame:
                        # Log hash to detect if frame content actually changes
                        frame_hash = frame[-20:]  # last 20 chars of base64 = unique fingerprint
                        agent._latest_frame = frame
                        agent._frame_received_at = time.time()
                        if _frame_injector_count[0] <= 5 or _frame_injector_count[0] % 15 == 0:
                            logger.info(f"[frame-injector] ✓ Got frame ({len(frame)//1024}KB) hash=...{frame_hash[-8:]} poll #{_frame_injector_count[0]}")
                    else:
                        if _frame_injector_count[0] <= 10:
                            logger.info(f"[frame-injector] No frame available (poll #{_frame_injector_count[0]}, room={agent._room_name})")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.info(f"[frame-injector] Error: {e}")

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

        # Start continuous recording for Voice Mode (captures between queries)
        if mode != "job" and getattr(agent, '_spatial_recorder', None) and agent._spatial_recorder._consent:
            await agent._spatial_recorder.start_continuous_recording(agent, interval=60)
            logger.info("[arrival-agent] ✓ Continuous recording started (Voice Mode)")

        # Wait for the session to end (room disconnect) then clean up tasks
        disconnect_event = asyncio.Event()

        @ctx.room.on("disconnected")
        def on_disconnect():
            logger.info("[arrival-agent] Room disconnected — cleaning up background tasks")
            disconnect_event.set()

        await disconnect_event.wait()

        # Cancel background tasks explicitly
        injector_task.cancel()
        if monitor_task:
            monitor_task.cancel()

        # End spatial recording session
        if getattr(agent, '_spatial_recorder', None):
            try:
                await agent._spatial_recorder.stop_continuous_recording()
                await agent._spatial_recorder.end_session()
            except Exception as e:
                logger.debug(f"[spatial] End session error: {e}")

        logger.info("[arrival-agent] ✓ Background tasks cancelled")

    except Exception as e:
        logger.error(f"[arrival-agent] ✗ ENTRYPOINT CRASHED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(server)
