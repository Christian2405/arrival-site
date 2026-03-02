"""
Feedback router — POST /api/feedback
Stores thumbs-up/down ratings on AI responses for quality tracking.
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import config
from app.middleware.auth import get_current_user

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
                    "question": request.question[:5000],  # Truncate long questions
                    "answer": request.answer[:10000],  # Truncate long answers
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
        return FeedbackResponse(success=True, id=feedback_id)

    except Exception as e:
        logger.error(f"[feedback] Failed to store feedback: {e}", exc_info=True)
        # Don't fail the request — feedback is non-critical
        return FeedbackResponse(success=False)
