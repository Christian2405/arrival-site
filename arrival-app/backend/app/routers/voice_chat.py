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
from app.services.diagnostic_flows import lookup_diagnostic_flow, format_diagnostic_context
from app.services.feedback_learning import get_feedback_context
from app.services.job_context import get_job_context, format_job_context_prompt
from app.middleware.auth import get_current_user
from app.services.usage import check_query_limit
from app.services.s3 import upload_clip, build_s3_key

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
    audio_chunks: list[str] | None = None  # Split TTS for faster first-sentence playback
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
    # Voice messages are short — cap at 500 chars each to keep input tokens low
    _content_limit = 500 if request.mode == "job" else 2000
    safe_history = [
        {
            "role": msg["role"],
            "content": str(msg.get("content", ""))[:_content_limit],
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

        # ALL MODES: Strip image unless transcript contains visual keywords.
        # Without this, Claude sees the camera frame and describes it even when
        # the user asks a non-visual question like "test" or "what size wire?".
        _visual_keywords = {
            "see", "look", "show", "camera", "picture", "photo", "image",
            "what's this", "what is this", "what's that", "what is that",
            "this look", "that look", "what do you", "point", "pointing",
            "check this", "check that", "wrong here", "wrong with",
            "identify", "read this", "read that", "model number",
            "what brand", "what model",
        }
        _transcript_lower = transcript.lower()
        _wants_visual = any(kw in _transcript_lower for kw in _visual_keywords)
        if not _wants_visual and request.image_base64:
            logger.info(f"[voice-chat] Stripping image — no visual keywords in: '{transcript[:40]}'")
            request.image_base64 = None

        # 2. Usage check + RAG doc search in parallel (searches both user + team namespaces)
        # All modes (text, voice, job) get full RAG access to manuals + uploaded docs.
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

        # Handle RAG results
        rag_context = rag_result if not isinstance(rag_result, Exception) else []
        if isinstance(rag_result, Exception):
            logger.warning(f"RAG retrieval failed: {rag_result}")

        if not usage["allowed"]:
            raise HTTPException(
                status_code=429,
                detail="Daily limit reached. Resets at midnight.",
            )
        logger.info(f"[voice-chat] Usage+RAG done in {time.monotonic()-t1:.2f}s (rag_results={len(rag_context)})")

        # Static error code lookup — instant, no latency
        error_code_result = lookup_error_code(transcript)
        error_code_context = format_error_code_context(error_code_result) if error_code_result else ""
        if error_code_result:
            logger.info(f"[voice-chat] Error code hit: {error_code_result['brand']} {error_code_result['code']}")

        # Diagnostic flow lookup — if no error code, check for symptom match
        diagnostic_context = ""
        if not error_code_result:
            diag_result = lookup_diagnostic_flow(transcript)
            if diag_result:
                diagnostic_context = format_diagnostic_context(diag_result)
                logger.info(f"[voice-chat] Diagnostic flow hit: {diag_result['title']}")

        # Feedback correction lookup — check if we've been corrected on similar questions
        fb_context = None
        try:
            fb_context = await get_feedback_context(transcript)
        except Exception as e:
            logger.debug(f"[voice-chat] Feedback context skipped: {e}")

        # Per-mode response tuning
        if request.mode == "job":
            voice_max_tokens = 150  # 1-3 spoken sentences — keep it tight for speed

            # Get job equipment context if set
            job_ctx = get_job_context(user_id)
            job_context_prompt = format_job_context_prompt(job_ctx) + "\n\n" if job_ctx else ""

            voice_prompt_prefix = (
                job_context_prompt +
                "You're a 50-year vet working alongside a tech on a job. You're their buddy — "
                "you talk about anything, answer anything. Short, confident, natural. "
                "1-3 sentences max. This is spoken aloud — don't drone on.\n\n"

                "RULES:\n"
                "- Answer what they asked, nothing extra. Simple question = simple answer.\n"
                "- Lead with the most likely cause. Don't list 5 things.\n"
                "- If they ask about a specific error code or blink code and you don't have verified data for it, "
                "say 'I don't have that code memorized — what does the chart on the unit show?' NEVER guess error codes.\n"
                "- If they ask something non-trade (weather, sports, lunch), just chat naturally. You're a person, not a manual.\n"
                "- If you tell them to check something, ask what they find.\n"
                "- If they confirm ('yeah I see it'), give the next step.\n"
                "- If they say 'it's fine' or 'no' or push back, DROP IT IMMEDIATELY. Say 'Fair enough' or 'Got it' and move on.\n"
                "- If they challenge something you said ('what are you talking about', 'there's no leak', 'that's wrong'), "
                "IMMEDIATELY back off. Say 'My bad' or 'Alright, scratch that'. NEVER double down. NEVER insist.\n"
                "- NEVER make something up. If you're not sure, say so. A wrong answer wastes the tech's time.\n"
                "- No filler: no 'Great question', no 'Let me know if you need anything'.\n"
                "- If image attached and they asked about it, reference it. Otherwise ignore it completely.\n\n"

                "EXAMPLES:\n"
                "Q: 'Superheat target on a TXV?' → 'Subcooling, not superheat — 10 to 12 degrees. What are you reading?'\n"
                "Q: 'Carrier keeps short cycling' → 'Flame sensor. Pull it, emery cloth, fixes it 80% of the time.'\n"
                "Q: 'What size wire for 40 amps?' → '8 gauge copper. Over 50 feet, bump to 6.'\n"
                "Q: 'Yeah I see the corrosion' → 'Emery cloth and NoOx. Want me to walk you through it?'\n"
                "Q: 'There's no leak here' → 'My bad, must have misread that. What are you looking at?'\n"
                "Q: 'What do you think about the Bears game?' → 'Don't get me started. What a season though.'\n"
            )
            if error_code_context:
                voice_prompt_prefix += "\n\n" + error_code_context
            elif diagnostic_context:
                voice_prompt_prefix += "\n\n" + diagnostic_context
            if fb_context:
                voice_prompt_prefix += "\n\n" + fb_context

            tts_voice_id = config.ELEVENLABS_JOB_VOICE_ID
            tts_voice_settings = {
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.0,
                "use_speaker_boost": True,
                "speed": 1.0,
            }
        else:
            voice_max_tokens = 200
            voice_prompt_prefix = (
                "Keep it to 1-3 sentences. This is spoken aloud — make it sound natural, not written.\n\n"

                "RULES:\n"
                "- Just answer the question they asked. Nothing else.\n"
                "- No 'Great question!' No 'I'd be happy to help.' No 'Let me know if you have other questions.'\n"
                "- Use contractions. Say 'you're' not 'you are', 'don't' not 'do not'.\n"
                "- Use 'probably', 'usually', 'most likely' — that's how people talk.\n"
                "- If they ask about a specific error code/blink code and you don't have verified data, "
                "say 'I don't have that code memorized — check the chart on the unit door.' NEVER guess error codes.\n"
                "- NEVER make something up. If you don't know a specific detail, say 'I'm not sure about that one.'\n"
                "- If an image is attached, ONLY describe it if the user explicitly asked about something visual "
                "(e.g. 'what do you see', 'look at this', 'what brand is this'). "
                "For ANY other question, COMPLETELY IGNORE the image.\n"
                "- Continue the conversation naturally. Don't repeat yourself.\n"
                "- NEVER volunteer observations about the image. NEVER say 'I can see...' unless they asked you to look.\n"
                "- If the user pushes back or says you're wrong, back off immediately. Say 'my bad' and move on.\n\n"

                "EXAMPLE RESPONSES (match this tone):\n"
                "Q: 'What causes a furnace to short cycle?'\n"
                "A: 'Usually it's a dirty flame sensor — pull it and clean it with emery cloth. If that's not it, check your filter, a clogged filter will overheat it and trip the limit switch.'\n\n"
                "Q: 'How do I check a capacitor?'\n"
                "A: 'Kill the power, discharge it, then put your meter on microfarads. Compare what you read to what's printed on the cap — if it's more than 10% off, swap it.'\n"
            )
            if error_code_context:
                voice_prompt_prefix += "\n\n" + error_code_context
            elif diagnostic_context:
                voice_prompt_prefix += "\n\n" + diagnostic_context
            if fb_context:
                voice_prompt_prefix += "\n\n" + fb_context

            tts_voice_id = None  # use default
            tts_voice_settings = None  # use default

        # 3. Call Claude chat — Sonnet for intelligence, prompts enforce brevity
        chat_result = await chat_with_claude(
            message=transcript,
            image_base64=request.image_base64,
            conversation_history=request.conversation_history,
            rag_context=rag_context,
            max_tokens=voice_max_tokens,
            system_prompt_prefix=voice_prompt_prefix,
            model=config.ANTHROPIC_VOICE_MODEL,
        )

        # 4. Convert AI response to speech (single TTS call — reliable, no cutoffs)
        audio_base64 = await text_to_speech(
            chat_result["response"],
            voice_id=tts_voice_id,
            voice_settings=tts_voice_settings,
        )

        total_elapsed = time.monotonic() - t0
        logger.info(f"[voice-chat] Total pipeline: {total_elapsed:.2f}s")

        # 5. Fire-and-forget: log query only (memory skipped for voice speed)
        _voice_elapsed_ms = int(total_elapsed * 1000)
        _voice_mode = "job" if request.mode == "job" else "voice"
        async def _log():
            await log_query(
                user_id=user_id,
                question=transcript,
                response=chat_result.get("response"),
                source=chat_result.get("source"),
                confidence=chat_result.get("confidence"),
                has_image=bool(request.image_base64),
                team_id=team_id,
                mode=_voice_mode,
                rag_chunks_used=chat_result.get("rag_chunks_used"),
                response_time_ms=_voice_elapsed_ms,
            )
        asyncio.create_task(_safe_task(_log(), task_name="voice_chat_log_query"))

        # 6. Fire-and-forget: spatial snapshot (frame + labels) when image present
        if request.image_base64 and _wants_visual:
            async def _spatial_snapshot():
                try:
                    import uuid
                    from datetime import datetime
                    from app.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, AWS_S3_BUCKET
                    import httpx as _httpx

                    _svc_headers = {
                        "apikey": SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=representation",
                    }

                    clip_id = str(uuid.uuid4())
                    now = datetime.utcnow()
                    s3_key = f"snapshots/{now.year}/{now.month:02d}/{now.day:02d}/{user_id[:8]}/{clip_id}.jpg"

                    # Upload JPEG to S3
                    frame_bytes = b64_module.b64decode(request.image_base64)
                    await upload_clip(s3_key, frame_bytes, content_type="image/jpeg")

                    # Log to spatial_clips
                    async with _httpx.AsyncClient() as client:
                        await client.post(
                            f"{SUPABASE_URL}/rest/v1/spatial_clips",
                            headers=_svc_headers,
                            json={
                                "id": clip_id,
                                "s3_key": s3_key,
                                "s3_bucket": AWS_S3_BUCKET,
                                "trigger_type": "voice_query",
                                "trigger_text": transcript[:2000],
                                "ai_response": chat_result.get("response", "")[:2000],
                                "status": "ready",
                                "resolution": "snapshot",
                                "file_size_bytes": len(frame_bytes),
                                "frame_count": 1,
                                "duration_seconds": 0,
                            },
                            timeout=10,
                        )

                        # Auto-labels
                        labels = [
                            {"clip_id": clip_id, "label_type": "semantic", "label_value": transcript[:500], "confidence": 1.0},
                        ]
                        if error_code_result:
                            labels.append({"clip_id": clip_id, "label_type": "equipment", "label_value": f"{error_code_result.get('brand', '')} {error_code_result.get('code', '')}", "confidence": 0.9})

                        await client.post(
                            f"{SUPABASE_URL}/rest/v1/spatial_labels",
                            headers=_svc_headers,
                            json=labels,
                            timeout=10,
                        )
                    logger.info(f"[spatial] Voice snapshot saved: {s3_key} ({len(frame_bytes)} bytes)")
                except Exception as e:
                    logger.debug(f"[spatial] Voice snapshot failed (non-fatal): {e}")
            asyncio.create_task(_safe_task(_spatial_snapshot(), task_name="voice_spatial_snapshot"))

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
