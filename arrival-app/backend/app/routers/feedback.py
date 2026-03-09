"""
Feedback router — POST /api/feedback
Stores thumbs-up/down ratings on AI responses for quality tracking.
On negative feedback with a comment, triggers the learning pipeline
to store the correction as a Mem0 memory for this user.
On any feedback, updates chunk_scores for the RAG data flywheel.
"""

import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import config
from app.middleware.auth import get_current_user
from app.services.feedback_learning import process_negative_feedback

logger = logging.getLogger(__name__)

router = APIRouter()


async def _update_chunk_scores(user_id: str, question: str, rating: str):
    """Look up which RAG chunks were used for this question and update their scores.
    Data flywheel: positive feedback boosts chunks, negative flags them."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        return

    try:
        import httpx

        # Find the most recent query matching this question
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/queries",
                headers={
                    "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                },
                params={
                    "user_id": f"eq.{user_id}",
                    "question": f"eq.{question[:500]}",
                    "order": "created_at.desc",
                    "limit": "1",
                    "select": "rag_chunks_used",
                },
            )
            if resp.status_code != 200:
                return
            rows = resp.json()
            if not rows or not rows[0].get("rag_chunks_used"):
                return

            chunks = rows[0]["rag_chunks_used"]
            if not isinstance(chunks, list) or not chunks:
                return

            # Update chunk_scores for each chunk
            column = "positive_count" if rating == "positive" else "negative_count"
            for chunk in chunks:
                chunk_id = chunk.get("id", "")
                if not chunk_id:
                    continue

                # Upsert: insert with count=1 or increment existing
                # Using RPC would be ideal, but simple upsert works for MVP
                # First try to get existing row
                get_resp = await client.get(
                    f"{config.SUPABASE_URL}/rest/v1/chunk_scores",
                    headers={
                        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                    },
                    params={"chunk_id": f"eq.{chunk_id}", "select": "positive_count,negative_count"},
                )

                if get_resp.status_code == 200 and get_resp.json():
                    # Update existing
                    existing = get_resp.json()[0]
                    new_val = existing.get(column, 0) + 1
                    await client.patch(
                        f"{config.SUPABASE_URL}/rest/v1/chunk_scores",
                        headers={
                            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                            "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                            "Content-Type": "application/json",
                        },
                        params={"chunk_id": f"eq.{chunk_id}"},
                        json={column: new_val, "last_updated": datetime.now(timezone.utc).isoformat()},
                    )
                else:
                    # Insert new
                    row = {
                        "chunk_id": chunk_id,
                        "namespace": "global_knowledge",
                        "positive_count": 1 if rating == "positive" else 0,
                        "negative_count": 1 if rating == "negative" else 0,
                    }
                    await client.post(
                        f"{config.SUPABASE_URL}/rest/v1/chunk_scores",
                        headers={
                            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                            "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                            "Content-Type": "application/json",
                        },
                        json=row,
                    )

            logger.info(f"[feedback] Updated chunk_scores for {len(chunks)} chunks ({rating})")

    except Exception as e:
        logger.warning(f"[feedback] Chunk score update failed (non-blocking): {e}")


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

        # Data flywheel: update chunk scores (fire-and-forget, both positive and negative)
        asyncio.create_task(_safe_task(
            _update_chunk_scores(user_id, request.question, request.rating),
            task_name="update_chunk_scores",
        ))

        return FeedbackResponse(success=True, id=feedback_id)

    except Exception as e:
        logger.error(f"[feedback] Failed to store feedback: {e}", exc_info=True)
        # Don't fail the request — feedback is non-critical
        return FeedbackResponse(success=False)
