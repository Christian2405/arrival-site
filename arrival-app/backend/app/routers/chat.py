"""
Chat router — POST /api/chat
Sends a message (optionally with camera image) to Claude, returns AI response.
Now includes: JWT auth, Mem0 memory retrieval/storage, RAG document context.

Performance paths:
  • Fast path — simple greetings/acknowledgements skip memory & RAG → ~2-3s
  • Full path  — everything in parallel (memory + team_id + RAG user-ns) → ~5-8s
"""

import asyncio
import json
import logging
import re
import time
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.demo import get_demo_chat_response
from app.services.anthropic import chat_with_claude, stream_chat_with_claude
from app.services.memory import retrieve_memories, store_memory
from app.services.rag import retrieve_context
from app.services.supabase import log_query, get_user_team_id
from app.services.error_codes import lookup_error_code, format_error_code_context
from app.services.diagnostic_flows import lookup_diagnostic_flow, format_diagnostic_context
from app.services.feedback_learning import get_feedback_context
from app.middleware.auth import get_current_user
from app.services.usage import check_query_limit

logger = logging.getLogger(__name__)

router = APIRouter()


MAX_MESSAGE_LENGTH = 10_000  # 10K chars
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB base64
MAX_HISTORY_ITEMS = 50


# --- Fast-path detection ---
# Simple messages that don't benefit from memory/RAG lookups.
_SIMPLE_MESSAGES = frozenset({
    "hello", "hi", "hey", "yo", "sup", "hiya",
    "thanks", "thank you", "thx", "cheers", "ta",
    "ok", "okay", "sure", "yep", "yup", "yeah", "yes", "no", "nah", "nope",
    "bye", "goodbye", "see ya", "later", "cya",
    "good morning", "good afternoon", "good evening", "gday", "g'day",
    "how are you", "whats up", "what's up",
})


def _is_simple_message(msg: str) -> bool:
    """Return True if the message is a simple greeting/acknowledgement."""
    cleaned = re.sub(r"[!?.,]+$", "", msg.strip().lower())
    return len(cleaned) < 40 and cleaned in _SIMPLE_MESSAGES


# Bug #37: Simple in-memory rate limiter for demo mode
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
        # If still too large after pruning, clear oldest half
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


# Bug #36: Safe task wrapper that catches and logs exceptions
async def _safe_task(coro, task_name: str = "background_task"):
    """Wrap a coroutine so exceptions are logged instead of swallowed."""
    try:
        await coro
    except asyncio.CancelledError:
        logger.debug(f"[{task_name}] Task cancelled")
    except Exception as e:
        logger.error(f"[{task_name}] Background task failed: {e}", exc_info=True)


class ChatRequest(BaseModel):
    message: str
    image_base64: str | None = None
    image_manual: bool = False
    conversation_history: list[dict] = []
    units: str = "imperial"


class ChatResponse(BaseModel):
    response: str
    source: str | None = None
    confidence: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req: Request,
    demo: bool = Query(False, description="Use demo mode (no API key needed)"),
):
    """
    AI Chat — send a question with an optional camera frame.
    Pass ?demo=true for canned trade responses without API keys.
    """
    t0 = time.monotonic()

    # Validate input sizes
    if len(request.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MAX_MESSAGE_LENGTH} chars)")
    if request.image_base64 and len(request.image_base64) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 10 MB)")
    if len(request.conversation_history) > MAX_HISTORY_ITEMS:
        raise HTTPException(status_code=400, detail=f"Conversation history too long (max {MAX_HISTORY_ITEMS} messages)")

    # Sanitize conversation_history — only allow valid roles, truncate content
    MAX_CONTENT_LENGTH = 10_000
    request.conversation_history = [
        {
            "role": msg["role"],
            "content": str(msg.get("content", ""))[:MAX_CONTENT_LENGTH],
        }
        for msg in request.conversation_history
        if isinstance(msg, dict)
        and msg.get("role") in ("user", "assistant")
        and msg.get("content")
    ]

    try:
        if demo:
            # Bug #37: Rate limit demo requests
            client_ip = req.client.host if req.client else "unknown"
            if not _check_demo_rate_limit(client_ip):
                raise HTTPException(
                    status_code=429,
                    detail=f"Demo rate limit exceeded. Max {DEMO_RATE_LIMIT} requests per minute."
                )
            result = get_demo_chat_response(request.message)

            elapsed = time.monotonic() - t0
            logger.info(f"[chat] Demo responded in {elapsed:.2f}s")
            return ChatResponse(
                response=result["response"],
                source=result.get("source"),
                confidence=result.get("confidence"),
            )
        else:
            # 1. Get authenticated user
            user = await get_current_user(req)
            user_id = user["user_id"]

            simple = _is_simple_message(request.message) and not request.image_base64
            team_id = None  # Will be set in full path

            if simple:
                # ── FAST PATH ── Skip memory & RAG for simple greetings
                logger.info(f"[chat] Fast path for '{request.message}' ({user_id[:8]}…)")
                result = await chat_with_claude(
                    message=request.message,
                    conversation_history=request.conversation_history,
                    max_tokens=150,
                    system_prompt_prefix=(
                        "Keep it to 1-2 sentences. Be friendly and conversational — "
                        "like a coworker, not a manual."
                    ),
                )

                # Fire-and-forget: store memory (no await)
                asyncio.create_task(_safe_task(
                    store_memory(user_id, [
                        {"role": "user", "content": request.message},
                        {"role": "assistant", "content": result["response"]},
                    ]),
                    task_name="store_memory",
                ))
            else:
                # ── FULL PATH ── Memory + team_id + RAG all in parallel for speed
                logger.info(f"[chat] Full path for '{request.message[:40]}…' ({user_id[:8]}…)")

                # Static lookups — instant, no I/O
                error_code_result = lookup_error_code(request.message)
                error_code_context = format_error_code_context(error_code_result) if error_code_result else None
                if error_code_result:
                    logger.info(f"[chat] Error code hit: {error_code_result['brand']} {error_code_result['code']}")

                diagnostic_context = None
                if not error_code_result:
                    diag_result = lookup_diagnostic_flow(request.message)
                    if diag_result:
                        diagnostic_context = format_diagnostic_context(diag_result)
                        logger.info(f"[chat] Diagnostic flow hit: {diag_result['title']}")

                # Run memory + team_id + feedback corrections in parallel first
                # (need team_id before RAG so we can search team namespace in one call)
                pre_results = await asyncio.gather(
                    retrieve_memories(user_id, request.message),
                    get_user_team_id(user_id),
                    get_feedback_context(request.message),
                    return_exceptions=True,
                )
                memories = pre_results[0] if not isinstance(pre_results[0], Exception) else []
                team_id = pre_results[1] if not isinstance(pre_results[1], Exception) else None
                feedback_context = pre_results[2] if not isinstance(pre_results[2], Exception) else None

                if isinstance(pre_results[0], Exception):
                    logger.warning(f"[chat] Memory retrieval failed: {pre_results[0]}")
                if isinstance(pre_results[1], Exception):
                    logger.warning(f"[chat] Team ID retrieval failed: {pre_results[1]}")
                if isinstance(pre_results[2], Exception):
                    logger.warning(f"[chat] Feedback context failed: {pre_results[2]}")

                # Single RAG call with team_id — searches user + global + team namespaces
                try:
                    rag_context = await asyncio.wait_for(
                        retrieve_context(user_id, request.message, team_id=team_id),
                        timeout=4.0,
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"[chat] RAG retrieval failed: {e}")
                    rag_context = []

                # Strip auto-captured images unless the message contains visual keywords.
                # Manually-attached images (user tapped camera/photo button) are always kept.
                if request.image_base64 and not request.image_manual:
                    _visual_keywords = {
                        "see", "look", "show", "camera", "picture", "photo", "image",
                        "what's this", "what is this", "what's that", "what is that",
                        "this look", "that look", "what do you", "point", "pointing",
                        "check this", "check that", "wrong here", "wrong with",
                        "identify", "read this", "read that", "model number",
                        "what brand", "what model", "diagnose", "what's the issue",
                        "what is the issue", "what's wrong", "this unit", "this thing",
                        "describe", "tell me about", "inspect", "analyze",
                    }
                    _msg_lower = request.message.lower()
                    if not any(kw in _msg_lower for kw in _visual_keywords):
                        logger.info(f"[chat] Stripping auto-captured image — no visual keywords in: '{request.message[:40]}'")
                        request.image_base64 = None

                # Build units instruction if user prefers metric
                units_note = "\n\nIMPORTANT: The user prefers METRIC units. Use Celsius, millimeters, liters, kilopascals, meters, etc. Convert any imperial measurements." if request.units == "metric" else ""

                # Call Claude with all context
                result = await chat_with_claude(
                    message=request.message,
                    image_base64=request.image_base64,
                    conversation_history=request.conversation_history,
                    user_memories=memories,
                    rag_context=rag_context,
                    max_tokens=1024,
                    system_prompt_prefix=(
                        "\n\n".join(filter(None, [error_code_context, diagnostic_context, feedback_context]))
                        + units_note
                    ),
                )

                # Fire-and-forget background tasks
                asyncio.create_task(_safe_task(
                    store_memory(user_id, [
                        {"role": "user", "content": request.message},
                        {"role": "assistant", "content": result["response"]},
                    ]),
                    task_name="store_memory",
                ))

        elapsed = time.monotonic() - t0
        elapsed_ms = int(elapsed * 1000)
        logger.info(f"[chat] Responded in {elapsed:.2f}s")

        # Log query with timing + mode (fire-and-forget, after elapsed is calculated)
        asyncio.create_task(_safe_task(
            _log_query(user_id, request, result, team_id=team_id if not simple else None, mode="text", response_time_ms=elapsed_ms),
            task_name="log_query",
        ))

        return ChatResponse(
            response=result["response"],
            source=result.get("source"),
            confidence=result.get("confidence"),
        )

    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        # Bug fix: Don't leak config/key info to clients
        if "not set" in error_msg.lower() or "api_key" in error_msg.lower():
            logger.error(f"Server config error: {error_msg}")
            raise HTTPException(status_code=500, detail="Service temporarily unavailable")
        raise HTTPException(status_code=400, detail="Invalid request parameters")
    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chat failed. Please try again.")


async def _log_query(
    user_id: str,
    request: ChatRequest,
    result: dict,
    team_id: str | None = None,
    mode: str = "text",
    response_time_ms: int | None = None,
):
    """Background helper to log the query to Supabase.
    Bug fix: Accept team_id as param to avoid redundant Supabase call."""
    if team_id is None:
        team_id = await get_user_team_id(user_id)
    await log_query(
        user_id=user_id,
        question=request.message,
        response=result.get("response"),
        source=result.get("source"),
        confidence=result.get("confidence"),
        has_image=bool(request.image_base64),
        team_id=team_id,
        mode=mode,
        rag_chunks_used=result.get("rag_chunks_used"),
        response_time_ms=response_time_ms,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    req: Request,
    demo: bool = Query(False),
):
    """
    Streaming AI Chat — same as /chat but returns Server-Sent Events.
    First token appears in ~1-2s instead of waiting 15-20s for full response.
    """
    t0 = time.monotonic()

    # Validate
    if len(request.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail="Message too long")
    if request.image_base64 and len(request.image_base64) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large")
    if len(request.conversation_history) > MAX_HISTORY_ITEMS:
        raise HTTPException(status_code=400, detail="History too long")

    request.conversation_history = [
        {"role": msg["role"], "content": str(msg.get("content", ""))[:10_000]}
        for msg in request.conversation_history
        if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content")
    ]

    if demo:
        client_ip = req.client.host if req.client else "unknown"
        if not _check_demo_rate_limit(client_ip):
            raise HTTPException(status_code=429, detail="Demo rate limit exceeded.")
        result = get_demo_chat_response(request.message)

        async def demo_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': result['response']})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'source': result.get('source'), 'confidence': result.get('confidence')})}\n\n"

        return StreamingResponse(demo_gen(), media_type="text/event-stream")

    # Authenticated path
    user = await get_current_user(req)
    user_id = user["user_id"]

    simple = _is_simple_message(request.message) and not request.image_base64

    async def stream_gen():
        nonlocal simple
        full_response = ""
        team_id = None
        rag_context = []

        try:
            if simple:
                logger.info(f"[chat-stream] Fast path for '{request.message}' ({user_id[:8]}…)")
                async for chunk in stream_chat_with_claude(
                    message=request.message,
                    conversation_history=request.conversation_history,
                    max_tokens=150,
                    system_prompt_prefix="Keep it to 1-2 sentences. Be friendly and conversational.",
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            else:
                logger.info(f"[chat-stream] Full path for '{request.message[:40]}…' ({user_id[:8]}…)")

                # Static lookups — instant
                error_code_result = lookup_error_code(request.message)
                error_code_context = format_error_code_context(error_code_result) if error_code_result else None

                diagnostic_context = None
                if not error_code_result:
                    diag_result = lookup_diagnostic_flow(request.message)
                    if diag_result:
                        diagnostic_context = format_diagnostic_context(diag_result)

                # Parallel context fetch
                parallel_results = await asyncio.gather(
                    retrieve_memories(user_id, request.message),
                    get_user_team_id(user_id),
                    retrieve_context(user_id, request.message),
                    get_feedback_context(request.message),
                    return_exceptions=True,
                )
                memories = parallel_results[0] if not isinstance(parallel_results[0], Exception) else []
                team_id = parallel_results[1] if not isinstance(parallel_results[1], Exception) else None
                rag_context = parallel_results[2] if not isinstance(parallel_results[2], Exception) else []
                feedback_context = parallel_results[3] if not isinstance(parallel_results[3], Exception) else None

                # Team RAG if applicable
                if team_id and rag_context is not None:
                    try:
                        team_rag = await asyncio.wait_for(
                            retrieve_context(user_id, request.message, team_id=team_id),
                            timeout=2.0,
                        )
                        existing_texts = {r["text"][:200] for r in rag_context}
                        for item in team_rag:
                            if item["text"][:200] not in existing_texts:
                                rag_context.append(item)
                        rag_context.sort(key=lambda x: x.get("score", 0), reverse=True)
                        rag_context = rag_context[:5]
                    except (asyncio.TimeoutError, Exception):
                        pass

                # Strip auto-captured images
                if request.image_base64 and not request.image_manual:
                    _visual_keywords = {
                        "see", "look", "show", "camera", "picture", "photo", "image",
                        "what's this", "what is this", "what's that", "what is that",
                        "this look", "that look", "what do you", "point", "pointing",
                        "check this", "check that", "wrong here", "wrong with",
                        "identify", "read this", "read that", "model number",
                        "what brand", "what model", "diagnose", "what's the issue",
                        "what is the issue", "what's wrong", "this unit", "this thing",
                        "describe", "tell me about", "inspect", "analyze",
                    }
                    if not any(kw in request.message.lower() for kw in _visual_keywords):
                        request.image_base64 = None

                units_note = "\n\nIMPORTANT: The user prefers METRIC units." if request.units == "metric" else ""

                # Stream Claude response
                async for chunk in stream_chat_with_claude(
                    message=request.message,
                    image_base64=request.image_base64,
                    conversation_history=request.conversation_history,
                    user_memories=memories,
                    rag_context=rag_context,
                    max_tokens=1024,
                    system_prompt_prefix=(
                        "\n\n".join(filter(None, [error_code_context, diagnostic_context, feedback_context]))
                        + units_note
                    ),
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

            # Final event with metadata
            source = "Claude AI Analysis"
            if rag_context:
                filenames = list(set(ctx["filename"] for ctx in rag_context))
                source = f"Claude AI + {', '.join(filenames[:2])}"
            yield f"data: {json.dumps({'type': 'done', 'source': source, 'confidence': 'medium'})}\n\n"

            elapsed = time.monotonic() - t0
            logger.info(f"[chat-stream] Responded in {elapsed:.2f}s")

            # Fire-and-forget logging
            asyncio.create_task(_safe_task(
                store_memory(user_id, [
                    {"role": "user", "content": request.message},
                    {"role": "assistant", "content": full_response},
                ]),
                task_name="store_memory",
            ))

        except Exception as e:
            logger.error(f"[chat-stream] Error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': 'Chat failed. Please try again.'})}\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")
