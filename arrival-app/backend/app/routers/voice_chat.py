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
from app.services.rag import retrieve_context
from app.services.supabase import log_query, get_user_team_id
from app.services.error_codes import lookup_error_code, format_error_code_context
from app.services.job_context import get_job_context, format_job_context_prompt
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


async def _safe_get_team_id(req: Request) -> str | None:
    """Get the user's team_id without blocking the pipeline if it fails."""
    try:
        user = await get_current_user(req)
        team_id = await get_user_team_id(user["user_id"])
        return team_id
    except Exception as e:
        logger.debug(f"[voice-chat] Team lookup failed (non-fatal): {e}")
        return None


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

        # --- Authenticated flow (optimized for speed) ---
        # Voice pipeline: STT + Auth + Team → RAG → Claude Haiku → TTS
        t0 = time.monotonic()

        # 1. Auth + STT + Team lookup all in parallel
        user_result, transcript, team_id_result = await asyncio.gather(
            get_current_user(req),
            transcribe_audio(request.audio_base64),
            asyncio.create_task(_safe_get_team_id(req)),
        )
        user_id = user_result["user_id"]
        team_id = team_id_result if not isinstance(team_id_result, Exception) else None

        if not transcript:
            raise HTTPException(status_code=400, detail="Could not transcribe audio — no speech detected")

        logger.info(f"[voice-chat] STT done in {time.monotonic()-t0:.2f}s: '{transcript[:50]}…' (team={team_id})")

        # 2. Usage check + RAG doc search in parallel (searches both user + team namespaces)
        t1 = time.monotonic()
        usage_result, rag_result = await asyncio.gather(
            check_query_limit(user_id),
            retrieve_context(user_id, transcript, team_id=team_id),
            return_exceptions=True,
        )

        # Handle usage check
        usage = usage_result if not isinstance(usage_result, Exception) else {"allowed": True}
        if isinstance(usage_result, Exception):
            logger.warning(f"Usage check failed: {usage_result}")
        if not usage["allowed"]:
            raise HTTPException(
                status_code=429,
                detail="Daily limit reached. Resets at midnight.",
            )

        # Handle RAG results
        rag_context = rag_result if not isinstance(rag_result, Exception) else []
        if isinstance(rag_result, Exception):
            logger.warning(f"RAG retrieval failed: {rag_result}")
        logger.info(f"[voice-chat] Usage+RAG done in {time.monotonic()-t1:.2f}s (rag_results={len(rag_context)})")

        # Static error code lookup — instant, no latency
        error_code_result = lookup_error_code(transcript)
        error_code_context = format_error_code_context(error_code_result) if error_code_result else ""
        if error_code_result:
            logger.info(f"[voice-chat] Error code hit: {error_code_result['brand']} {error_code_result['code']}")

        # Per-mode response tuning
        if request.mode == "job":
            voice_max_tokens = 200

            # Get job equipment context if set
            job_ctx = get_job_context(user_id)
            job_context_prompt = format_job_context_prompt(job_ctx) + "\n\n" if job_ctx else ""

            voice_prompt_prefix = (
                job_context_prompt +
                "You're a knowledgeable coworker helping a tradesperson. "
                "The user is talking to you — answer whatever they ask. "
                "They might ask about a job, specs from a document, how to do something, "
                "or just a general question they didn't want to type out. "
                "A camera image may be attached but ONLY use it if the user explicitly asks about something visual "
                "(e.g. 'what is this?', 'what do you see?', 'what's wrong here?'). "
                "For any other question, completely ignore the image and answer based on the spoken question only. "
                "Never describe the camera view, never say you can see their workspace, never comment on image quality. "
                "Keep responses to 2-4 sentences. "
                "Continue the conversation naturally. Don't repeat yourself."
            )
            if error_code_context:
                voice_prompt_prefix += "\n\n" + error_code_context

            tts_voice_id = config.ELEVENLABS_JOB_VOICE_ID
            tts_voice_settings = {
                "stability": 0.6,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": False,
                "speed": 1.15,
            }
        else:
            voice_max_tokens = 150
            voice_prompt_prefix = (
                "Keep your response to 1-3 sentences max. Spoken aloud. "
                "The user is talking instead of typing — answer whatever they ask. "
                "A camera image may be attached but ONLY reference it if the user explicitly asks about something visual. "
                "For any other question, ignore the image completely. Never describe what the camera shows. "
                "Continue the conversation naturally. Don't repeat yourself."
            )
            if error_code_context:
                voice_prompt_prefix += "\n\n" + error_code_context

            tts_voice_id = None  # use default
            tts_voice_settings = None  # use default

        # 3. Call Claude chat — use fast voice model (Haiku) for low latency
        chat_result = await chat_with_claude(
            message=transcript,
            image_base64=request.image_base64,
            conversation_history=request.conversation_history,
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
        logger.info(f"[voice-chat] Total pipeline: {total_elapsed:.2f}s")

        # 5. Fire-and-forget: log query only (memory skipped for voice speed)
        async def _log():
            await log_query(
                user_id=user_id,
                question=transcript,
                response=chat_result.get("response"),
                source=chat_result.get("source"),
                confidence=chat_result.get("confidence"),
                has_image=bool(request.image_base64),
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
