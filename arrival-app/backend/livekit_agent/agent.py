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

# ---------------------------------------------------------------------------
# Real-Time Guidance config
# ---------------------------------------------------------------------------
GUIDANCE_CHECK_INTERVAL = 4     # Seconds between camera checks during guidance
GUIDANCE_MAX_STEPS = 12         # Max steps in a guided procedure
GUIDANCE_STEP_VERIFY_TOKENS = 200  # More tokens for detailed step verification

# Engagement scoring
ENGAGEMENT_INITIAL = 50
ENGAGEMENT_BOOST = 15       # User engaged with observation
ENGAGEMENT_DECAY = 10       # User ignored observation
ENGAGEMENT_MIN = 10
ENGAGEMENT_MAX = 100
ENGAGEMENT_RESPONSE_WINDOW = 30  # seconds to wait for user response

# Engagement stopwords — common words to exclude when checking if user
# responded to an observation (module-level for performance)
ENGAGEMENT_STOPWORDS = frozenset({
    "the", "a", "an", "is", "it", "that", "this", "what", "yeah",
    "yes", "no", "ok", "okay", "i", "you", "we", "my", "its",
    "was", "were", "are", "been", "be", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "can",
    "just", "about", "so", "but", "and", "or", "if", "not",
    "don't", "doesn't", "to", "in", "on", "of", "for", "at",
})

# ---------------------------------------------------------------------------
# Voice prompts
# ---------------------------------------------------------------------------

JOB_MODE_PROMPT = (
    # ── WHO YOU ARE ──
    "You are Arrival — an AI assistant for anyone doing hands-on work. "
    "HVAC, plumbing, electrical, construction, drywall, painting, roofing, carpentry, "
    "appliance repair, auto repair — you help with ALL of it. No job is too small or "
    "too niche. If someone asks for help, you help.\n\n"

    # ── CAMERA ──
    "You have a live camera feed from the user's phone. It is ALWAYS on. "
    "You can see what they see right now. When they ask 'what do you see' or "
    "'what am I looking at' — answer immediately from the frame. "
    "Never say 'let me take a look' or 'show me' — you're already watching.\n\n"

    # ── VISION ──
    "VISION:\n"
    "- Describe what you ACTUALLY see in the frame. Be honest and accurate.\n"
    "- If you can read text, model numbers, labels, or error codes — read them out.\n"
    "- If you spot a safety issue, wrong part, or bad technique — speak up.\n"
    "- Be specific when you can: 'That's a Carrier furnace' not 'I see some equipment.'\n"
    "- NEVER HALLUCINATE. If you can't clearly identify something, say so: "
    "'I can see something there but can't quite make it out.' "
    "Never invent objects, colors, wires, or equipment that aren't clearly visible.\n"
    "- Never complain about image quality. No 'blurry', 'too dark', 'unclear'. "
    "Work with the frame you have.\n"
    "- Never say 'I can't see' or 'I don't have camera access' — the camera is always on.\n\n"

    # ── TOOLS ──
    "TOOLS:\n"
    "- lookup_error_code: For error codes, blink codes, fault codes. Try this FIRST.\n"
    "- search_knowledge: For specs, sizing, manuals, building codes, installation details. "
    "Use this whenever you're not 100% sure of a number or spec.\n"
    "- start_guidance: When the user wants to be walked through a procedure step by step. "
    "Builds a guided procedure and activates camera-assisted guidance.\n"
    "- advance_guidance: Move to the next step when the user says 'done'/'next' or "
    "you can see they've completed the current step.\n\n"

    # ── HOW TO TALK ──
    "CONVERSATION:\n"
    "- This is spoken aloud. Keep it to 1-3 sentences. Don't drone on.\n"
    "- Answer what they asked, nothing extra.\n"
    "- Lead with the most likely answer. Don't list 5 possibilities.\n"
    "- Use trade terms naturally: AFUE, SEER, BTU, CFM, AWG, NEC.\n"
    "- Give specific numbers: '10 AWG, 30A breaker' not 'appropriate wire size.'\n"
    "- Use contractions. Sound like a person, not a manual.\n"
    "- Words like 'probably', 'usually', '9 times out of 10' — that's natural.\n"
    "- No filler. No 'Great question!' No 'Let me know if you need anything.'\n"
    "- If they push back, back off. 'Fair enough.' Never double down.\n"
    "- If they say stop or be quiet, say 'Got it' and go silent.\n"
    "- Never say 'consult a professional' — they are the professional.\n"
    "- Never dismiss any job. Wallpaper, paint touch-up, squeaky door — help them.\n"
    "- Never make something up. If you don't know, say 'I'm not sure on that one.'\n"
    "- For error codes: use lookup_error_code first, then search_knowledge. "
    "If both miss, say 'I don't have that code — what does the chart on the unit show?'\n\n"

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
        # User context — populated from participant metadata at session start
        self._user_id: str = "unknown"
        self._team_id: Optional[str] = None
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
        # Consecutive failure tracking for proactive analysis
        self._proactive_consecutive_failures: int = 0
        # Error code pre-injection tracking
        self._has_injected_codes: bool = False
        # Real-Time Guidance state
        self._guidance_active: bool = False
        self._guidance_task: str = ""           # "replacing capacitor on Carrier 24ACC"
        self._guidance_steps: list[str] = []    # ordered steps from procedure
        self._guidance_current_step: int = 0    # index into _guidance_steps
        self._guidance_context: str = ""        # RAG context for the procedure
        self._guidance_step_confirmed: bool = False  # camera confirmed current step done
        self._guidance_advancing: bool = False  # lock to prevent double-advance race
        # Equipment context (sent from frontend)
        self._equipment_type: str = ""
        self._equipment_brand: str = ""
        self._equipment_model: str = ""

    def get_guidance_state(self) -> dict:
        """Serialize guidance state for persistence/data channel."""
        if not self._guidance_active:
            return {"active": False}
        return {
            "active": True,
            "task": self._guidance_task,
            "steps": self._guidance_steps,
            "current_step": self._guidance_current_step,
        }

    def restore_guidance_state(self, state: dict):
        """Restore guidance state from data channel (on reconnect)."""
        if not state.get("active"):
            return
        steps = state.get("steps", [])
        if not steps:
            return
        self._guidance_active = True
        self._guidance_task = state.get("task", "")
        self._guidance_steps = steps
        self._guidance_current_step = min(state.get("current_step", 0), len(steps) - 1)
        self._guidance_step_confirmed = False
        logger.info(f"[guidance] ✓ Restored guidance state: step {self._guidance_current_step+1}/{len(steps)} for '{self._guidance_task}'")

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
        if not self._last_analyzed_hash:
            return True
        diff = sum(a != b for a, b in zip(new_hash, self._last_analyzed_hash))
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

    async def on_user_turn_completed(self, turn_ctx, new_message):
        """Inject the latest camera frame into the LLM context before every response.
        This makes vision truly always-on — the LLM sees the camera on every turn."""
        from livekit.agents.llm import ImageContent
        frame = self._latest_frame if (
            self._latest_frame and (time.time() - self._frame_received_at) < 30
        ) else None
        if frame:
            data_url = f"data:image/jpeg;base64,{frame}"
            image_content = ImageContent(image=data_url)
            # Prepend the frame + equipment context to the user's message
            eq_str = self._equipment_context_str()
            camera_label = "[LIVE CAMERA — this is what the tech's phone camera shows RIGHT NOW]"
            if eq_str:
                camera_label += f"\n[Equipment: {eq_str}]"
            new_message.content = [
                image_content,
                camera_label,
            ] + list(new_message.content)

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
        """Start step-by-step Real-Time Guidance for a task. Use when the tech asks you to
        walk them through something, guide them, or help them do a procedure step by step.
        Examples: 'walk me through replacing this capacitor', 'guide me through this install',
        'help me step by step', 'what do I do first'."""
        logger.info(f"[guidance] ★ Starting guidance: {task_description}")

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

        # 2. Use Claude to extract ordered steps from knowledge + task
        client = _get_anthropic_client()
        # Equipment context for more accurate procedures
        eq_str = self._equipment_context_str()
        eq_note = f"\nEquipment: {eq_str}\n" if eq_str else ""

        step_prompt = (
            "You're a 50-year trade veteran coaching a tech through a job in real time. "
            "They're on-site right now with their phone camera.\n\n"
            f"TASK: {task_description}\n{eq_note}\n"
        )
        if rag_context:
            step_prompt += f"REFERENCE MATERIAL:\n{rag_context}\n\n"

        step_prompt += (
            "Break this into key milestones — not a mundane checklist, but the critical "
            "waypoints a vet would naturally walk someone through. Think of it like you're "
            "standing right there: what would you tell them to do first, then next?\n\n"
            "Rules:\n"
            "- 4-8 milestones max. Each one is a meaningful action or check.\n"
            "- ALWAYS start with safety (kill power, shut gas, verify zero-energy)\n"
            "- Use specific tool/part names: '⅜ inch wrench', '10mm socket', not 'appropriate tool'\n"
            "- Write how you'd SAY it, not how you'd write a manual\n"
            "- Include what they should SEE or FEEL to know it's done right\n"
            "- End with a verification milestone (test, check for leaks, power up)\n\n"
            "Format: Return ONLY numbered milestones, one per line. No intro text.\n"
            "Example:\n"
            "1. Kill the power at the disconnect and verify with your meter — should read 0V\n"
            "2. Pop the access panel (4 phillips screws) and find the capacitor — silver or black cylinder near the contactor\n"
            "3. Discharge it with an insulated screwdriver across the terminals — you'll see a small spark\n"
        )

        try:
            response = await client.messages.create(
                model=config.ANTHROPIC_VISION_MODEL,  # Sonnet for better procedure quality
                max_tokens=800,
                messages=[{"role": "user", "content": step_prompt}],
            )
            steps_text = response.content[0].text.strip()
        except Exception as e:
            logger.error(f"[guidance] Failed to generate steps: {e}")
            return "I couldn't put together a procedure for that. Tell me what you're trying to do and I'll help you through it."

        # 3. Parse steps
        steps = []
        for line in steps_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip leading number/bullet: "1. ", "1) ", "- "
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
            cleaned = re.sub(r"^[-•]\s*", "", cleaned)
            if cleaned and len(cleaned) > 5:
                steps.append(cleaned)

        if not steps:
            return "I couldn't break that down into steps. Just tell me where you're at and I'll guide you."

        # Limit steps
        steps = steps[:GUIDANCE_MAX_STEPS]

        # 4. Activate guidance mode
        self._guidance_active = True
        self._guidance_task = task_description
        self._guidance_steps = steps
        self._guidance_current_step = 0
        self._guidance_context = rag_context
        self._guidance_step_confirmed = False

        logger.info(f"[guidance] ✓ Loaded {len(steps)} steps for: {task_description}")
        for i, step in enumerate(steps):
            logger.info(f"[guidance]   Step {i+1}: {step[:80]}")

        # 5. Return first step context to the LLM
        total = len(steps)
        return (
            f"## REAL-TIME GUIDANCE ACTIVE\n"
            f"Task: {task_description}\n\n"
            f"FIRST UP: {steps[0]}\n\n"
            f"Your game plan ({total} milestones):\n" +
            "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)) +
            "\n\nIMPORTANT — HOW TO GUIDE:\n"
            "- Talk like a veteran buddy coaching them, NOT like a manual.\n"
            "- DON'T say 'Step 1', 'Step 2' etc. Just tell them what to do naturally.\n"
            "- Use the camera: 'See that silver cylinder? That's your capacitor.'\n"
            "- Be specific: tool sizes, part names, what they should see/hear/feel.\n"
            "- When they finish, use advance_guidance to move to the next milestone.\n"
            "- They can interrupt you anytime with questions — answer and continue guiding.\n"
            "Start by telling them what to do first. Keep it conversational."
        )

    @function_tool()
    async def advance_guidance(self, reason: str) -> str:
        """Move to the next step in the guided procedure. Use when the tech says 'done',
        'next', 'what's next', 'ok', or when you can see through the camera that they
        completed the current step."""
        if not self._guidance_active or not self._guidance_steps:
            return "No active guidance to advance."

        # Prevent race condition: camera auto-advance and LLM tool call may fire simultaneously
        if self._guidance_advancing:
            return "Already advancing — hold on."
        self._guidance_advancing = True
        try:
            return self._do_advance_guidance(reason)
        finally:
            self._guidance_advancing = False

    def _do_advance_guidance(self, reason: str) -> str:
        """Internal advance logic — separated so the lock wraps it cleanly."""
        self._guidance_current_step += 1
        step_num = self._guidance_current_step
        total = len(self._guidance_steps)

        if step_num >= total:
            # All steps complete
            self._guidance_active = False
            task = self._guidance_task
            self._guidance_task = ""
            self._guidance_steps = []
            self._guidance_current_step = 0
            self._guidance_context = ""
            logger.info(f"[guidance] ✓ All {total} steps complete for: {task}")
            return (
                f"## GUIDANCE COMPLETE\n"
                f"Task: {task}\n"
                "That's it — they're done. Give them a quick 'nice work' and remind them to do "
                "a final check (test the system, check for leaks, verify operation). "
                "Keep it brief and encouraging. Don't recap all the steps."
            )

        current_step = self._guidance_steps[step_num]
        self._guidance_step_confirmed = False
        logger.info(f"[guidance] → Step {step_num + 1}/{total}: {current_step[:60]}")

        return (
            f"## NEXT UP: {current_step}\n"
            f"(Milestone {step_num + 1} of {total})\n\n"
            "Guide them naturally — DON'T say 'step 2' or 'next step'. "
            "Just tell them what to do next like a buddy would: 'Alright, now grab your...' "
            "Use the camera to reference what you see. Be specific about tools and what "
            "they should see/hear/feel when it's done right."
        )

    @function_tool()
    async def previous_step(self, reason: str) -> str:
        """Go back to the previous step in guidance. Use when the tech says 'go back',
        'wait', 'previous step', 'repeat that', 'what was the last step', or when they
        need to redo something."""
        if not self._guidance_active or not self._guidance_steps:
            return "No active guidance to go back in."

        if self._guidance_current_step <= 0:
            current_step = self._guidance_steps[0]
            return (
                f"Already at step 1 — there's no previous step.\n"
                f"Current step: {current_step}\n"
                "Re-explain this step to the tech clearly."
            )

        self._guidance_current_step -= 1
        step_num = self._guidance_current_step
        total = len(self._guidance_steps)
        current_step = self._guidance_steps[step_num]
        self._guidance_step_confirmed = False
        logger.info(f"[guidance] ← Back to step {step_num + 1}/{total}: {current_step[:60]}")

        return (
            f"## GOING BACK: {current_step}\n"
            f"(Milestone {step_num + 1} of {total})\n\n"
            "The tech wants to go back. Re-explain this naturally — "
            "maybe approach it from a different angle, or add more detail. "
            "DON'T say 'going back to step X'. Just say something like 'OK let's revisit that...' "
            "Use the camera to reference what you see."
        )

    @function_tool()
    async def repeat_step(self) -> str:
        """Repeat/re-explain the current guidance step. Use when the tech says 'say that again',
        'repeat', 'what was that', 'what step am I on', 'can you explain that again'."""
        if not self._guidance_active or not self._guidance_steps:
            return "No active guidance right now."

        step_num = self._guidance_current_step
        if step_num >= len(self._guidance_steps):
            return "Guidance is complete — all steps done."

        total = len(self._guidance_steps)
        current_step = self._guidance_steps[step_num]
        logger.info(f"[guidance] ↻ Repeating step {step_num + 1}/{total}")

        return (
            f"## REPEATING: {current_step}\n"
            f"(Milestone {step_num + 1} of {total})\n\n"
            "The tech wants to hear this again. Explain it differently — maybe simpler, "
            "maybe with more detail about what they should see. Use the camera to point things out."
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
    equipment_context: str = "",
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
                            + (f"Equipment: {equipment_context}\n" if equipment_context else "")
                            + f"{conv_context}{obs_context}\n\n"
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
                            "- NEVER HALLUCINATE. Only describe what is CLEARLY visible. If you can't identify "
                            "something with confidence, respond NOTHING. Do NOT invent colors, equipment, wires, "
                            "or objects that aren't obviously there.\n"
                            "- NEVER complain about image quality — no 'blurry', 'dark', 'unclear'. Work with what you have or say NOTHING.\n"
                            "- A shadow is not a leak. A stain is not active water. A wall is just a wall.\n"
                            "- When in doubt, say NOTHING. False positives destroy trust.\n\n"
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
    # Filter out quality complaints — the model should never say this
    _lower = result.lower()
    if any(w in _lower for w in ("blurry", "blur", "too dark", "unclear", "out of focus", "can't make out")):
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


async def _analyze_frame_guidance(
    frame_b64: str,
    current_step: str,
    step_num: int,
    total_steps: int,
    task: str,
    conversation_context: list[dict] | None = None,
    equipment_context: str = "",
) -> Optional[tuple[str, str]]:
    """
    Analyze a frame during Real-Time Guidance.
    Returns: (status, observation) or None.
    status: "DONE" (step complete), "WORKING" (in progress), "ISSUE" (problem), "SAFETY" (danger)
    """
    client = _get_anthropic_client()

    conv_context = ""
    if conversation_context:
        lines = []
        for msg in conversation_context[-3:]:
            role = "Tech" if msg.get("role") == "user" else "You"
            lines.append(f"- {role}: {msg.get('content', '')[:80]}")
        conv_context = "\nRecent conversation:\n" + "\n".join(lines) + "\n"

    response = await asyncio.wait_for(
        client.messages.create(
            model=config.ANTHROPIC_VISION_MODEL,
            max_tokens=GUIDANCE_STEP_VERIFY_TOKENS,
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
                            "You're guiding a tech through a job, watching through their phone camera.\n\n"
                            f"TASK: {task}\n"
                            + (f"EQUIPMENT: {equipment_context}\n" if equipment_context else "")
                            + f"CURRENT MILESTONE ({step_num}/{total_steps}): {current_step}\n"
                            f"{conv_context}\n"
                            "Look at what the camera shows. Respond in this EXACT format (one line):\n"
                            "STATUS|observation\n\n"
                            "STATUS must be one of:\n"
                            "- DONE: The current step appears to be completed based on what you see\n"
                            "- WORKING: Tech is actively working on this step — you can see progress\n"
                            "- ISSUE: Something looks wrong — wrong tool, wrong part, incorrect technique\n"
                            "- SAFETY: Immediate danger — stop and alert\n"
                            "- WAITING: Nothing happening yet, or camera isn't showing relevant action\n\n"
                            "Your observation should be specific and actionable — reference what you ACTUALLY SEE.\n"
                            "NEVER HALLUCINATE. Only describe what is clearly visible. If you can't see the work area "
                            "or can't confirm the step, use WAITING — don't invent progress or objects.\n"
                            "NEVER complain about image quality. No 'blurry', 'dark', 'unclear'.\n\n"
                            "Examples:\n"
                            "DONE|I can see the disconnect is flipped off and the panel is open\n"
                            "WORKING|You're getting those screws out, looks like 2 more to go\n"
                            "ISSUE|That looks like a ¼ inch wrench but you need ⅜ for those fittings\n"
                            "SAFETY|Hold on — I can see the disconnect is still on, kill the power first\n"
                            "WAITING|Standing by — point the camera at the work area when you're ready"
                        ),
                    },
                ],
            }],
        ),
        timeout=15.0,
    )
    result = response.content[0].text.strip()

    # Parse STATUS|observation
    parts = result.split("|", 1)
    if len(parts) == 2:
        status = parts[0].strip().upper()
        observation = parts[1].strip()
        if status in ("DONE", "WORKING", "ISSUE", "SAFETY", "WAITING"):
            return (status, observation)

    # Fallback
    return ("WORKING", result)


def _get_speech_instruction(severity: str, observation: str, agent: "ArrivalAgent") -> str:
    """Generate varied, natural speech instructions based on severity and context."""
    obs_count = len(agent._recent_observations)
    time_since_last = time.time() - agent._last_proactive_time if agent._last_proactive_time else 999

    if severity == "SAFETY":
        templates = [
            f"Alert the tech immediately — this is a safety issue: {observation}",
            f"Stop what you're doing — {observation}",
            f"Hold on, I see something: {observation}",
            f"Hey, heads up: {observation}",
        ]
        return random.choice(templates)
    elif obs_count == 0:
        # First observation on this job
        templates = [
            f"You just got a look at what they're working on. Mention casually: {observation}",
            f"Alright, I can see what you're working with. {observation}",
            f"OK so looking at this — {observation}",
        ]
        return random.choice(templates)
    elif time_since_last < 60:
        # Recent follow-up
        templates = [
            f"While they're still working on this, you also noticed: {observation}",
            f"Also noticing: {observation}",
            f"One more thing — {observation}",
            f"And just so you know: {observation}",
        ]
        return random.choice(templates)
    else:
        # After a gap (> 60s since last observation)
        templates = [
            f"Hey, one more thing you're seeing: {observation}",
            f"Hey, something I'm seeing: {observation}",
            f"Just spotted something: {observation}",
        ]
        return random.choice(templates)


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
    last_guidance_check = 0

    while True:
        try:
            # Guidance mode: check faster (every 3s). Normal mode: 5s (or 15s if failing)
            if agent._guidance_active:
                check_interval = GUIDANCE_CHECK_INTERVAL
            elif agent._proactive_consecutive_failures >= 3:
                check_interval = 15
            else:
                check_interval = PROACTIVE_CHECK_INTERVAL
            await asyncio.sleep(check_interval)

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

            # ── GUIDANCE MODE: Step verification via camera ──
            if agent._guidance_active and agent._guidance_steps:
                step_idx = agent._guidance_current_step
                if step_idx < len(agent._guidance_steps):
                    current_step = agent._guidance_steps[step_idx]
                    total = len(agent._guidance_steps)

                    # Don't check too frequently
                    if (now - last_guidance_check) < GUIDANCE_CHECK_INTERVAL:
                        continue
                    last_guidance_check = now

                    try:
                        guidance_result = await _analyze_frame_guidance(
                            frame,
                            current_step=current_step,
                            step_num=step_idx + 1,
                            total_steps=total,
                            task=agent._guidance_task,
                            conversation_context=list(agent._conversation_context),
                            equipment_context=agent._equipment_context_str(),
                        )
                    except Exception as e:
                        logger.warning(f"[guidance] Vision check failed: {e}")
                        continue

                    if not guidance_result:
                        continue

                    status, observation = guidance_result
                    logger.info(f"[guidance] Step {step_idx+1}/{total} → {status}: {observation[:60]}")

                    if status == "SAFETY":
                        # Safety always interrupts — even during guidance
                        await session.generate_reply(
                            instructions=f"STOP — safety issue during guided task: {observation}. Alert the tech immediately."
                        )
                    elif status == "DONE":
                        # Step complete — advance to next
                        # Race guard: if LLM tool is already advancing, skip
                        if agent._guidance_advancing:
                            logger.info("[guidance] Camera saw DONE but LLM is already advancing — skipping")
                            continue
                        agent._guidance_advancing = True
                        agent._guidance_step_confirmed = True
                        next_idx = step_idx + 1
                        if next_idx >= total:
                            # All steps done!
                            agent._guidance_active = False
                            logger.info(f"[guidance] ✓ All {total} steps complete!")
                            await session.generate_reply(
                                instructions=(
                                    f"They just finished everything for: {agent._guidance_task}. "
                                    f"Camera shows: {observation}. "
                                    "Give them a quick 'nice work!' and remind them to do a final check — "
                                    "test the system, check for leaks, verify operation. Keep it brief."
                                )
                            )
                            agent._guidance_task = ""
                            agent._guidance_steps = []
                            agent._guidance_current_step = 0
                        else:
                            # Move to next step
                            agent._guidance_current_step = next_idx
                            next_step = agent._guidance_steps[next_idx]
                            agent._guidance_step_confirmed = False
                            await session.generate_reply(
                                instructions=(
                                    f"That looks good — camera shows: {observation}. "
                                    f"Now guide them to: {next_step}. "
                                    "DON'T say 'step {next_idx+1}' or 'next step'. Just tell them naturally "
                                    "what to do next, like 'Alright, now...' or 'OK so next thing...'. "
                                    "Use the camera to point things out."
                                )
                            )
                        agent._guidance_advancing = False
                    elif status == "ISSUE":
                        # Problem detected — speak up but don't block
                        # Only mention issues if not actively speaking (avoid interrupting)
                        if (now - agent._last_user_speech_time) > 4:
                            await session.generate_reply(
                                instructions=(
                                    f"You spotted something: {observation}. "
                                    "Mention it casually but clearly — don't alarm them unless it's dangerous. "
                                    "Something like 'Hey, hold on — that looks like...' or 'Quick thing...'"
                                )
                            )
                    # WORKING and WAITING: just keep monitoring, don't speak

                continue  # Skip normal proactive analysis during guidance

            # ── NORMAL PROACTIVE MODE ──
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
                    equipment_context=agent._equipment_context_str(),
                )
                # Reset consecutive failure counter on successful analysis
                if agent._proactive_consecutive_failures > 0:
                    logger.info(f"[proactive] Analysis succeeded after {agent._proactive_consecutive_failures} failures — resetting interval to {PROACTIVE_CHECK_INTERVAL}s")
                agent._proactive_consecutive_failures = 0
            except Exception as e:
                agent._proactive_consecutive_failures += 1
                if agent._proactive_consecutive_failures >= 3:
                    logger.warning(f"[proactive] Vision failed {agent._proactive_consecutive_failures}x in a row: {e} — backing off to 15s")
                else:
                    logger.warning(f"[proactive] Vision failed ({agent._proactive_consecutive_failures}/3): {e}")
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
        team_id = None

        for participant in ctx.room.remote_participants.values():
            if participant.metadata:
                try:
                    meta = json.loads(participant.metadata)
                    user_id = meta.get("user_id", user_id)
                    mode = meta.get("mode", mode)
                    team_id = meta.get("team_id")  # None if user has no team
                except (json.JSONDecodeError, TypeError):
                    pass
                break

        logger.info(f"[arrival-agent] Room={room_name} user={user_id} mode={mode} team={team_id or 'none'}")

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

            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass

        logger.info("[arrival-agent] ✓ Data channel listener registered")

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

        @session.on("user_input_transcribed")
        def on_user_speech(ev):
            agent._last_user_speech_time = time.time()
            transcript = getattr(ev, "text", "") or getattr(ev, "transcript", "") or ""
            if not transcript:
                return

            text_lower = transcript.lower().strip()

            # Store conversation context (for proactive analyzer) — 10 messages = 5 turns
            agent._conversation_context.append({"role": "user", "content": transcript})
            if len(agent._conversation_context) > 10:
                agent._conversation_context.pop(0)

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
                step_idx = agent._guidance_current_step
                total = len(agent._guidance_steps)
                agent._guidance_active = False
                agent._guidance_task = ""
                agent._guidance_steps = []
                agent._guidance_current_step = 0
                agent._guidance_context = ""
                # Reset prompt to clean state
                agent.instructions = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                agent._has_injected_codes = False
                logger.info(f"[guidance] User exited guidance at step {step_idx+1}/{total}: '{text_lower}'")
                # Acknowledge — don't just go silent
                asyncio.ensure_future(session.generate_reply(
                    instructions=(
                        f"The tech just said '{transcript}' to end guidance (was on step {step_idx+1} of {total} for: {task}). "
                        "Acknowledge casually and encouragingly — something like 'Alright, you got it!' or "
                        "'Sounds good, holler if you need me.' Keep it short and warm, don't recap steps."
                    )
                ))
                return

            # Inject guidance context + error code context into prompt (merged, not exclusive)
            if agent._guidance_active and agent._guidance_steps:
                step_idx = agent._guidance_current_step
                if step_idx < len(agent._guidance_steps):
                    current_step = agent._guidance_steps[step_idx]
                    total = len(agent._guidance_steps)
                    base = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                    guidance_inject = (
                        f"\n\n## REAL-TIME GUIDANCE ACTIVE\n"
                        f"Task: {agent._guidance_task}\n"
                        f"Currently guiding on: {current_step}\n"
                        f"(Milestone {step_idx+1} of {total})\n\n"
                        f"Full game plan:\n" +
                        "\n".join(
                            f"{'→ ' if i == step_idx else '  '}{i+1}. {s}"
                            for i, s in enumerate(agent._guidance_steps)
                        ) +
                        "\n\nYou're coaching them through this live. IMPORTANT RULES:\n"
                        "- NEVER say 'step 1', 'step 2', etc. Guide naturally like a buddy.\n"
                        "- If they ask a question, answer it and stay on the current milestone.\n"
                        "- Use the camera to reference what you see.\n"
                        "- When they finish (say 'done'/'next' or camera shows it), use advance_guidance.\n"
                        "- They can interrupt anytime — that's fine, answer and continue."
                    )
                    # Merge: guidance + error code (if user asked about a code mid-guidance)
                    agent.instructions = base + guidance_inject + error_inject
            else:
                # No guidance active — just base + error codes (if any)
                base = (JOB_MODE_PROMPT if mode == "job" else DEFAULT_MODE_PROMPT) + VOICE_KNOWLEDGE
                agent.instructions = base + error_inject

            # Detect mute commands — entire utterance must exactly match a mute phrase
            # to avoid false positives like "stop valve testing" or "that's quiet today"
            if text_lower in _MUTE_PHRASES:
                agent._proactive_muted_until = time.time() + PROACTIVE_MUTE_DURATION
                agent._awaiting_engagement = False
                logger.info(f"[proactive] Muted for {PROACTIVE_MUTE_DURATION}s — user said: '{text_lower}'")
                return

            # Detect pushback — only on short utterances (< 8 words)
            word_count = len(text_lower.split())
            if word_count <= 7 and any(phrase in text_lower for phrase in _PUSHBACK_PHRASES):
                agent._user_pushback_count += 1
                agent._awaiting_engagement = False
                logger.info(f"[proactive] Pushback #{agent._user_pushback_count} — user said: '{text_lower}'")
                return

            # Engagement detection — did user respond to our observation?
            if agent._awaiting_engagement and agent._last_observation_text:
                elapsed = time.time() - agent._engagement_timer_start
                if elapsed < ENGAGEMENT_RESPONSE_WINDOW:
                    # Check if response is related — require 2+ non-stopword keyword matches
                    # or any question mark (user is asking about what was said)
                    obs_words = set(agent._last_observation_text.lower().split())
                    user_words = set(text_lower.split())
                    overlap = (obs_words & user_words) - ENGAGEMENT_STOPWORDS
                    if len(overlap) >= 2 or "?" in transcript:
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
                if len(agent._conversation_context) > 10:
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
        logger.info("[arrival-agent] ✓ Background tasks cancelled")

    except Exception as e:
        logger.error(f"[arrival-agent] ✗ ENTRYPOINT CRASHED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(server)
