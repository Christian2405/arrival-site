"""
Chat router — POST /api/chat
Sends a message (optionally with camera image) to Claude, returns AI response.
Now includes: JWT auth, Mem0 memory retrieval/storage, RAG document context.

Performance paths:
  • Fast path — simple greetings/acknowledgements skip memory & RAG → ~2-3s
  • Full path  — everything in parallel (memory + team_id + RAG user-ns) → ~5-8s
"""

import asyncio
import logging
import re
import time
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.demo import get_demo_chat_response
from app.services.anthropic import chat_with_claude
from app.services.memory import retrieve_memories, store_memory
from app.services.rag import retrieve_context
from app.services.supabase import log_query, get_user_team_id
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
    conversation_history: list[dict] = []


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
        else:
            # 1. Get authenticated user
            user = await get_current_user(req)
            user_id = user["user_id"]

            # 2. Check query limit
            usage = await check_query_limit(user_id)
            if not usage["allowed"]:
                raise HTTPException(
                    status_code=429,
                    detail="Daily limit reached. Resets at midnight.",
                )

            simple = _is_simple_message(request.message) and not request.image_base64

            if simple:
                # ── FAST PATH ── Skip memory & RAG for simple greetings
                logger.info(f"[chat] Fast path for '{request.message}' ({user_id[:8]}…)")
                result = await chat_with_claude(
                    message=request.message,
                    conversation_history=request.conversation_history,
                    max_tokens=150,
                    system_prompt_prefix=(
                        "You are Arrival AI, a helpful assistant for trade workers. "
                        "Be warm, friendly, and concise — 1-2 sentences max."
                    ),
                )

                # Fire-and-forget: store memory + log (no await)
                asyncio.create_task(_safe_task(
                    store_memory(user_id, [
                        {"role": "user", "content": request.message},
                        {"role": "assistant", "content": result["response"]},
                    ]),
                    task_name="store_memory",
                ))
                asyncio.create_task(_safe_task(
                    _log_query(user_id, request, result),
                    task_name="log_query",
                ))
            else:
                # ── FULL PATH ── Memory + team_id + RAG(user-ns) all in parallel
                logger.info(f"[chat] Full path for '{request.message[:40]}…' ({user_id[:8]}…)")

                # Bug fix: return_exceptions=True so one failed service
                # doesn't kill the entire request
                phase_results = await asyncio.gather(
                    retrieve_memories(user_id, request.message),
                    get_user_team_id(user_id),
                    retrieve_context(user_id, request.message, team_id=None),
                    return_exceptions=True,
                )
                memories = phase_results[0] if not isinstance(phase_results[0], Exception) else []
                team_id = phase_results[1] if not isinstance(phase_results[1], Exception) else None
                user_rag = phase_results[2] if not isinstance(phase_results[2], Exception) else []
                if isinstance(phase_results[0], Exception):
                    logger.warning(f"[chat] Memory retrieval failed: {phase_results[0]}")
                if isinstance(phase_results[1], Exception):
                    logger.warning(f"[chat] Team ID retrieval failed: {phase_results[1]}")
                if isinstance(phase_results[2], Exception):
                    logger.warning(f"[chat] RAG retrieval failed: {phase_results[2]}")

                # If user belongs to a team, quick async team-namespace search
                rag_context = user_rag
                if team_id:
                    try:
                        # Bug fix: Add timeout to team namespace RAG search
                        team_rag = await asyncio.wait_for(
                            retrieve_context(user_id, request.message, team_id=team_id),
                            timeout=4.0,
                        )
                        # Merge team results that aren't duplicates
                        seen = {r["text"][:200] for r in rag_context}
                        for r in team_rag:
                            if r["text"][:200] not in seen:
                                rag_context.append(r)
                                seen.add(r["text"][:200])
                        rag_context.sort(key=lambda x: x["score"], reverse=True)
                        rag_context = rag_context[:5]
                    except Exception as e:
                        logger.warning(f"[chat] Team RAG search failed (continuing): {e}")

                # Call Claude with all context
                result = await chat_with_claude(
                    message=request.message,
                    image_base64=request.image_base64,
                    conversation_history=request.conversation_history,
                    user_memories=memories,
                    rag_context=rag_context,
                    max_tokens=300,
                    system_prompt_prefix="Keep responses concise — 2-4 sentences for simple questions, more detail only when the user asks a technical or safety question.",
                )

                # Fire-and-forget background tasks
                asyncio.create_task(_safe_task(
                    store_memory(user_id, [
                        {"role": "user", "content": request.message},
                        {"role": "assistant", "content": result["response"]},
                    ]),
                    task_name="store_memory",
                ))
                asyncio.create_task(_safe_task(
                    _log_query(user_id, request, result, team_id=team_id),
                    task_name="log_query",
                ))

        elapsed = time.monotonic() - t0
        logger.info(f"[chat] Responded in {elapsed:.2f}s")

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


async def _log_query(user_id: str, request: ChatRequest, result: dict, team_id: str | None = None):
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
    )
