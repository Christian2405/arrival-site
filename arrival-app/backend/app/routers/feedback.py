"""
Feedback router — POST /api/feedback
Stores thumbs-up/down ratings on AI responses for quality tracking.
On negative feedback with a comment, triggers the learning pipeline
to store the correction as a Mem0 memory for this user.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import config
from app.middleware.auth import get_current_user
from app.services.feedback_learning import process_negative_feedback

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: str  # "positive" or "negative"
    feedback_text: str | None = None
    source: str | None = None
    conversation_id: str | None = None


class FeedbackResponse(BaseModel):
    success: bool
    id: str | None = None


# Bug #36 pattern: safe task wrapper
async def _safe_task(coro, task_name: str = "background_task"):
    """Wrap a coroutine so exceptions are logged instead of swallowed."""
    try:
        await coro
    except asyncio.CancelledError:
        logger.debug(f"[{task_name}] Task cancelled")
    except Exception as e:
        logger.error(f"[{task_name}] Background task failed: {e}", exc_info=True)


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, req: Request):
    """Submit feedback (thumbs up/down) on an AI response."""

    # Validate rating
    if request.rating not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="Rating must be 'positive' or 'negative'")

    # Get authenticated user
    user = await get_current_user(req)
    user_id = user["user_id"]

    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        logger.warning("[feedback] Supabase not configured — skipping feedback storage")
        return FeedbackResponse(success=False)

    try:
        import httpx
        # Get the user's token for RLS
        auth_header = req.headers.get("Authorization", "")
        user_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{config.SUPABASE_URL}/rest/v1/feedback",
                headers={
                    "apikey": config.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {user_token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                json={
                    "user_id": user_id,
                    "question": request.question[:5000],
                    "answer": request.answer[:10000],
                    "rating": request.rating,
                    "feedback_text": (request.feedback_text or "")[:2000] if request.feedback_text else None,
                    "source": request.source,
                    "conversation_id": request.conversation_id,
                },
            )
            resp.raise_for_status()
            rows = resp.json()
            feedback_id = rows[0]["id"] if rows else None

        logger.info(f"[feedback] {request.rating} from {user_id[:8]}… (id={feedback_id})")

        # Trigger learning pipeline for negative feedback (fire-and-forget)
        if request.rating == "negative" and feedback_id:
            asyncio.create_task(_safe_task(
                process_negative_feedback(
                    feedback_id=feedback_id,
                    user_id=user_id,
                    question=request.question,
                    answer=request.answer,
                    feedback_text=request.feedback_text,
                ),
                task_name="process_negative_feedback",
            ))

        return FeedbackResponse(success=True, id=feedback_id)

    except Exception as e:
        logger.error(f"[feedback] Failed to store feedback: {e}", exc_info=True)
        # Don't fail the request — feedback is non-critical
        return FeedbackResponse(success=False)
