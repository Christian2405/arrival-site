"""
Voice Chat router — POST /api/voice-chat
Composite endpoint that combines STT + Chat + TTS into a single round-trip
for faster voice responses. Accepts audio, returns transcript + AI response + audio.
"""

import asyncio
import base64 as b64_module
import logging
import re as re_module
import time
from typing import Literal
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
from app.services.usage import check_query_limit

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

    # Prune stale entries to prevent unbounded memory growth.
    # Evict expired entries instead of clearing all (avoids thundering herd).
    if len(_demo_rate_limits) > 5000:
        expired = [k for k, (_, ws) in _demo_rate_limits.items()
                   if now - ws > DEMO_RATE_WINDOW * 2]
        for k in expired:
            del _demo_rate_limits[k]
        if len(_demo_rate_limits) > 5000:
            to_remove = sorted(_demo_rate_limits, key=lambda k: _demo_rate_limits[k][1])[:2500]
            for k in to_remove:
                del _demo_rate_limits[k]

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
    mode: Literal["default", "job"] = "default"


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

    # Validate base64 encoding (lightweight check — avoid full decode to save memory)
    if not re_module.match(r'^[A-Za-z0-9+/\n]+=*$', request.audio_base64[:1000]):
        raise HTTPException(status_code=400, detail="Invalid audio data format")

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
        and isinstance(msg.get("content"), str)
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
        t0 = time.monotonic()

        # Detect follow-up: if conversation already has ≥2 messages, skip
        # slow memory/RAG lookups — context is in the conversation history.
        is_followup = len(request.conversation_history) >= 2

        # 1. Auth + STT in parallel (always needed)
        user_result, transcript = await asyncio.gather(
            get_current_user(req),
            transcribe_audio(request.audio_base64),
        )
        user_id = user_result["user_id"]

        # Check query limit before proceeding
        usage = await check_query_limit(user_id)
        if not usage["allowed"]:
            raise HTTPException(
                status_code=429,
                detail="Daily limit reached. Resets at midnight.",
            )

        if not transcript:
            raise HTTPException(status_code=400, detail="Could not transcribe audio — no speech detected")

        logger.info(f"[voice-chat] STT done in {time.monotonic()-t0:.2f}s: '{transcript[:50]}…'")

        # 2. Context fetch — skip on follow-ups for speed (~2-4s saved)
        team_id = None
        memories: list = []
        rag_context: list = []

        if is_followup:
            logger.info("[voice-chat] Follow-up detected — skipping memory/RAG")
        else:
            t1 = time.monotonic()
            phase_results = await asyncio.gather(
                get_user_team_id(user_id),
                retrieve_memories(user_id, transcript),
                retrieve_context(user_id, transcript, team_id=None),
                return_exceptions=True,
            )
            team_id = phase_results[0] if not isinstance(phase_results[0], Exception) else None
            memories = phase_results[1] if not isinstance(phase_results[1], Exception) else []
            rag_context = phase_results[2] if not isinstance(phase_results[2], Exception) else []
            if isinstance(phase_results[0], Exception):
                logger.warning(f"Team ID retrieval failed: {phase_results[0]}")
            if isinstance(phase_results[1], Exception):
                logger.warning(f"Memory retrieval failed: {phase_results[1]}")
            if isinstance(phase_results[2], Exception):
                logger.warning(f"RAG retrieval failed: {phase_results[2]}")
            logger.info(f"[voice-chat] Context fetched in {time.monotonic()-t1:.2f}s")

        # Per-mode response tuning
        if request.mode == "job":
            voice_max_tokens = 200
            voice_prompt_prefix = (
                "You're a coworker standing next to a tradesperson on a job site. "
                "You can see what they see through their camera and you're listening to them. "
                "Keep responses to 2-4 sentences. "
                "If the user responds to something you just said (like an alert or suggestion), "
                "continue the conversation naturally — pick up where you left off. "
                "Don't repeat yourself. Don't re-explain things you already said. "
                "If an image is attached but unclear or blurry, ignore it and answer the spoken question. "
                "Never comment on image quality. "
                "Describe what you actually see, not what you think it might be. "
                "If you're not sure what something is, describe it rather than guessing."
            )
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
            voice_prompt_prefix = (
                "Keep your response to 1-3 sentences max. The user is hearing this spoken aloud. "
                "A camera image may be attached. ONLY reference the image if the user's question is about something they're looking at "
                "(e.g. 'what is this?', 'what's wrong here?'). "
                "If they ask a general question, ignore the image and just answer it. "
                "If the image is unclear or blurry, ignore it. Never comment on image quality. "
                "Describe what you actually see — don't guess. "
                "If the user is responding to something you said, continue the conversation naturally. "
                "Don't repeat yourself or re-ask questions they already answered."
            )
            tts_voice_id = None  # use default
            tts_voice_settings = None  # use default

        # 3. Call Claude chat — use fast voice model (Haiku) for low latency
        chat_result = await chat_with_claude(
            message=transcript,
            image_base64=request.image_base64,
            conversation_history=request.conversation_history,
            user_memories=memories,
            rag_context=rag_context,
            max_tokens=voice_max_tokens,
            system_prompt_prefix=voice_prompt_prefix,
            model=config.ANTHROPIC_VOICE_MODEL,
        )

        # 4. Convert AI response to speech (TTS)
        audio_base64 = await text_to_speech(
            chat_result["response"],
            voice_id=tts_voice_id,
            voice_settings=tts_voice_settings,
        )

        total_elapsed = time.monotonic() - t0
        logger.info(f"[voice-chat] Total pipeline: {total_elapsed:.2f}s (followup={is_followup})")

        # 5. Fire-and-forget: store memory + log query
        asyncio.create_task(_safe_task(
            store_memory(user_id, [
                {"role": "user", "content": transcript},
                {"role": "assistant", "content": chat_result["response"]},
            ]),
            task_name="voice_chat_store_memory",
        ))

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
