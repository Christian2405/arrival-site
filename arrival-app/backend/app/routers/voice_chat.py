"""
Voice Chat router — POST /api/voice-chat
Composite endpoint that combines STT + Chat + TTS into a single round-trip
for faster voice responses. Accepts audio, returns transcript + AI response + audio.
"""

import asyncio
import base64 as b64_module
import logging
import time
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app import config
from app.services.demo import get_demo_transcription, get_demo_chat_response, generate_silent_audio_base64
from app.services.deepgram import transcribe_audio
from app.services.anthropic import chat_with_claude
from app.services.elevenlabs import text_to_speech
from app.services.memory import retrieve_memories, store_memory
from app.services.rag import retrieve_context
from app.services.supabase import log_query, get_user_team_id
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB raw; base64 is ~1.37x larger
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB base64
MAX_HISTORY_ITEMS = 50
MAX_CONTENT_LENGTH = 10_000


# Simple in-memory rate limiter for demo mode (same pattern as chat.py)
_demo_rate_limits: dict[str, tuple[int, float]] = {}  # IP -> (count, window_start)
DEMO_RATE_LIMIT = 10      # max requests
DEMO_RATE_WINDOW = 60.0   # per 60 seconds


def _check_demo_rate_limit(ip: str) -> bool:
    """
    Check if this IP has exceeded the demo rate limit.
    Returns True if the request should be allowed, False if rate limited.
    """
    now = time.time()

    # Prune stale entries if dict is too large to prevent unbounded growth
    if len(_demo_rate_limits) > 10000:
        _demo_rate_limits.clear()

    if ip in _demo_rate_limits:
        count, window_start = _demo_rate_limits[ip]
        if now - window_start > DEMO_RATE_WINDOW:
            # Window expired, reset
            _demo_rate_limits[ip] = (1, now)
            return True
        elif count >= DEMO_RATE_LIMIT:
            return False
        else:
            _demo_rate_limits[ip] = (count + 1, window_start)
            return True
    else:
        _demo_rate_limits[ip] = (1, now)
        return True


# Safe task wrapper that catches and logs exceptions (same pattern as chat.py)
async def _safe_task(coro, task_name: str = "background_task"):
    """Wrap a coroutine so exceptions are logged instead of swallowed."""
    try:
        await coro
    except asyncio.CancelledError:
        logger.debug(f"[{task_name}] Task cancelled")
    except Exception as e:
        logger.error(f"[{task_name}] Background task failed: {e}", exc_info=True)


class VoiceChatRequest(BaseModel):
    audio_base64: str
    image_base64: str | None = None
    conversation_history: list[dict] = []
    mode: str = "default"


class VoiceChatResponse(BaseModel):
    transcript: str
    response: str
    audio_base64: str
    source: str | None = None
    confidence: str | None = None


@router.post("/voice-chat", response_model=VoiceChatResponse)
async def voice_chat(
    request: VoiceChatRequest,
    req: Request,
    demo: bool = Query(False, description="Use demo mode (no API key needed)"),
):
    """
    Voice Chat — composite STT + Chat + TTS in a single round-trip.
    Accepts audio (and optional image), returns transcript, AI response, and TTS audio.
    Pass ?demo=true for canned responses without API keys.
    """
    # Validate input sizes
    if len(request.audio_base64) < 100:
        raise HTTPException(status_code=400, detail="Audio data too short")
    if len(request.audio_base64) > MAX_AUDIO_SIZE * 1.37:
        raise HTTPException(status_code=400, detail="Audio too large (max 10 MB)")

    # Validate base64 encoding
    try:
        b64_module.b64decode(request.audio_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")

    if request.image_base64 and len(request.image_base64) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 10 MB)")
    if request.image_base64:
        try:
            b64_module.b64decode(request.image_base64, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
    if len(request.conversation_history) > MAX_HISTORY_ITEMS:
        raise HTTPException(
            status_code=400,
            detail=f"Conversation history too long (max {MAX_HISTORY_ITEMS} messages)",
        )

    # Sanitize conversation_history — only allow valid roles, truncate content
    safe_history = [
        {
            "role": msg["role"],
            "content": str(msg.get("content", ""))[:MAX_CONTENT_LENGTH],
        }
        for msg in request.conversation_history
        if isinstance(msg, dict)
        and msg.get("role") in ("user", "assistant")
        and msg.get("content")
    ]

    # Enforce alternating user/assistant roles (required by Claude API)
    cleaned_history: list[dict] = []
    for msg in safe_history:
        if cleaned_history and cleaned_history[-1]["role"] == msg["role"]:
            cleaned_history[-1]["content"] += "\n" + msg["content"]
        else:
            cleaned_history.append(msg)
    request.conversation_history = cleaned_history

    try:
        if demo:
            # Rate limit demo requests
            client_ip = req.client.host if req.client else "unknown"
            if not _check_demo_rate_limit(client_ip):
                raise HTTPException(
                    status_code=429,
                    detail=f"Demo rate limit exceeded. Max {DEMO_RATE_LIMIT} requests per minute.",
                )

            # Demo mode: use canned responses
            transcript = get_demo_transcription()
            chat_result = get_demo_chat_response(transcript)
            audio_base64 = generate_silent_audio_base64(duration_seconds=0.5)

            return VoiceChatResponse(
                transcript=transcript,
                response=chat_result["response"],
                audio_base64=audio_base64,
                source=chat_result.get("source"),
                confidence=chat_result.get("confidence"),
            )

        # --- Authenticated flow ---

        # 1. Get authenticated user
        user = await get_current_user(req)
        user_id = user["user_id"]

        # 2. Transcribe audio (STT)
        transcript = await transcribe_audio(request.audio_base64)

        if not transcript:
            raise HTTPException(status_code=400, detail="Could not transcribe audio — no speech detected")

        # 3. Concurrently fetch team_id + user memories, then RAG context
        phase1_results = await asyncio.gather(
            get_user_team_id(user_id),
            retrieve_memories(user_id, transcript),
            return_exceptions=True,
        )
        team_id = phase1_results[0] if not isinstance(phase1_results[0], Exception) else None
        memories = phase1_results[1] if not isinstance(phase1_results[1], Exception) else []
        if isinstance(phase1_results[0], Exception):
            logger.warning(f"Team ID retrieval failed: {phase1_results[0]}")
        if isinstance(phase1_results[1], Exception):
            logger.warning(f"Memory retrieval failed: {phase1_results[1]}")

        # Fetch RAG context (depends on team_id from phase 1)
        try:
            rag_context = await retrieve_context(user_id, transcript, team_id=team_id)
        except Exception as exc:
            logger.warning(f"RAG retrieval failed: {exc}")
            rag_context = []

        # Per-mode response tuning
        if request.mode == "job":
            voice_max_tokens = 200
            voice_prompt_prefix = "You are having a natural, calm conversation with a tradesperson on a job site. Be conversational, warm, and helpful. Keep responses to 2-4 sentences."
            tts_voice_id = config.ELEVENLABS_JOB_VOICE_ID
            tts_voice_settings = {
                "stability": 0.6,
                "similarity_boost": 0.75,
                "style": 0.15,
                "use_speaker_boost": True,
                "speed": 1.0,
            }
        else:
            voice_max_tokens = 150
            voice_prompt_prefix = "IMPORTANT: Keep your response to 1-3 sentences maximum. Be direct and concise — the user is hearing this spoken aloud on a job site."
            tts_voice_id = None  # use default
            tts_voice_settings = None  # use default

        # 4. Call Claude chat with transcribed text + image + memories + RAG context + history
        chat_result = await chat_with_claude(
            message=transcript,
            image_base64=request.image_base64,
            conversation_history=request.conversation_history,
            user_memories=memories,
            rag_context=rag_context,
            max_tokens=voice_max_tokens,
            system_prompt_prefix=voice_prompt_prefix,
        )

        # 5. Convert AI response to speech (TTS)
        audio_base64 = await text_to_speech(
            chat_result["response"],
            voice_id=tts_voice_id,
            voice_settings=tts_voice_settings,
        )

        # 6. Fire-and-forget: store memory
        asyncio.create_task(_safe_task(
            store_memory(user_id, [
                {"role": "user", "content": transcript},
                {"role": "assistant", "content": chat_result["response"]},
            ]),
            task_name="voice_chat_store_memory",
        ))

        # 7. Fire-and-forget: log query for team activity
        async def _log():
            await log_query(
                user_id=user_id,
                question=transcript,
                response=chat_result.get("response"),
                source=chat_result.get("source"),
                confidence=chat_result.get("confidence"),
                has_image=bool(request.image_base64),
                team_id=team_id,
            )
        asyncio.create_task(_safe_task(_log(), task_name="voice_chat_log_query"))

        return VoiceChatResponse(
            transcript=transcript,
            response=chat_result["response"],
            audio_base64=audio_base64,
            source=chat_result.get("source"),
            confidence=chat_result.get("confidence"),
        )

    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        if "not set" in error_msg.lower() or "api_key" in error_msg.lower():
            logger.error(f"Server config error: {error_msg}")
            raise HTTPException(status_code=500, detail="Service temporarily unavailable")
        logger.warning(f"Validation error in voice chat: {error_msg}")
        raise HTTPException(status_code=400, detail="Invalid request parameters")
    except Exception as e:
        logger.error(f"Voice chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Voice chat failed. Please try again.")
