"""
Chat router — POST /api/chat
Sends a message (optionally with camera image) to Claude, returns AI response.
Now includes: JWT auth, Mem0 memory retrieval/storage, RAG document context.
"""

import asyncio
import logging
import time
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.demo import get_demo_chat_response
from app.services.anthropic import chat_with_claude
from app.services.memory import retrieve_memories, store_memory
from app.services.rag import retrieve_context
from app.services.supabase import log_query, get_user_team_id
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


MAX_MESSAGE_LENGTH = 10_000  # 10K chars
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB base64
MAX_HISTORY_ITEMS = 50


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

            # 2. Retrieve memories for this user
            memories = await retrieve_memories(user_id, request.message)

            # Bug #1: Look up the user's team_id so we can search team documents too
            team_id = await get_user_team_id(user_id)

            # 3. Retrieve relevant document context (RAG) — include team namespace
            rag_context = await retrieve_context(user_id, request.message, team_id=team_id)

            # 4. Call Claude with memories + RAG context
            result = await chat_with_claude(
                message=request.message,
                image_base64=request.image_base64,
                conversation_history=request.conversation_history,
                user_memories=memories,
                rag_context=rag_context,
            )

            # 5. Store new memories (fire-and-forget, non-blocking)
            # Bug #36: Use safe wrapper to log exceptions
            asyncio.create_task(_safe_task(
                store_memory(user_id, [
                    {"role": "user", "content": request.message},
                    {"role": "assistant", "content": result["response"]},
                ]),
                task_name="store_memory",
            ))

            # 6. Log query for team activity (fire-and-forget, non-blocking)
            # Bug #36: Use safe wrapper to log exceptions
            async def _log():
                log_team_id = team_id or await get_user_team_id(user_id)
                await log_query(
                    user_id=user_id,
                    question=request.message,
                    response=result.get("response"),
                    source=result.get("source"),
                    confidence=result.get("confidence"),
                    has_image=bool(request.image_base64),
                    team_id=log_team_id,
                )
            asyncio.create_task(_safe_task(_log(), task_name="log_query"))

        return ChatResponse(
            response=result["response"],
            source=result.get("source"),
            confidence=result.get("confidence"),
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chat failed. Please try again.")
