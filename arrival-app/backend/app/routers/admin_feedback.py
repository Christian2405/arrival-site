"""
Admin feedback review — lets the founder review negative feedback,
write corrections, and promote corrections to the global knowledge base.

Auth: simple secret-based (ADMIN_SECRET env var). Good enough for a solo founder.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
import httpx

from app import config

logger = logging.getLogger(__name__)

router = APIRouter()

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def _check_admin(secret: str):
    """Verify admin secret."""
    if not ADMIN_SECRET or secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


def _supa_headers():
    """Service role headers for Supabase."""
    return {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# List feedback
# ---------------------------------------------------------------------------

@router.get("/admin/feedback")
async def list_feedback(
    secret: str = Query(""),
    rating: str = Query("negative"),
    reviewed: bool = Query(False),
    limit: int = Query(50, le=200),
):
    """List feedback entries for admin review."""
    _check_admin(secret)

    async with httpx.AsyncClient(timeout=10.0) as client:
        params = {
            "rating": f"eq.{rating}",
            "reviewed": f"eq.{str(reviewed).lower()}",
            "order": "created_at.desc",
            "limit": str(limit),
            "select": "id,user_id,question,answer,rating,feedback_text,correction,reviewed,promoted_to_knowledge,created_at",
        }
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/feedback",
            headers=_supa_headers(),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Submit correction
# ---------------------------------------------------------------------------

class CorrectionRequest(BaseModel):
    correction: str


@router.post("/admin/feedback/{feedback_id}/correct")
async def submit_correction(
    feedback_id: str,
    body: CorrectionRequest,
    secret: str = Query(""),
    promote: bool = Query(False),
):
    """Write a correction for a negative feedback entry. Optionally promote to Pinecone."""
    _check_admin(secret)

    # Update Supabase record
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{config.SUPABASE_URL}/rest/v1/feedback",
            headers={**_supa_headers(), "Prefer": "return=representation"},
            params={"id": f"eq.{feedback_id}"},
            json={
                "correction": body.correction[:2000],
                "reviewed": True,
                "promoted_to_knowledge": promote,
            },
        )
        resp.raise_for_status()
        rows = resp.json()

    if not rows:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Promote to Pinecone if requested
    if promote:
        feedback = rows[0]
        asyncio.create_task(_safe_promote(feedback_id, feedback, body.correction))

    return {"success": True, "promoted": promote, "id": feedback_id}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/admin/feedback/stats")
async def feedback_stats(secret: str = Query("")):
    """Aggregate feedback stats for the dashboard."""
    _check_admin(secret)

    counts = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for rating in ("positive", "negative"):
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/feedback",
                headers={**_supa_headers(), "Prefer": "count=exact"},
                params={"rating": f"eq.{rating}", "select": "id", "limit": "0"},
            )
            resp.raise_for_status()
            # Content-Range header: */N where N is total count
            range_header = resp.headers.get("content-range", "*/0")
            counts[rating] = int(range_header.split("/")[-1])

        # Unreviewed negative count
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/feedback",
            headers={**_supa_headers(), "Prefer": "count=exact"},
            params={
                "rating": "eq.negative",
                "reviewed": "eq.false",
                "select": "id",
                "limit": "0",
            },
        )
        resp.raise_for_status()
        range_header = resp.headers.get("content-range", "*/0")
        unreviewed = int(range_header.split("/")[-1])

    return {
        "total_positive": counts.get("positive", 0),
        "total_negative": counts.get("negative", 0),
        "unreviewed_negative": unreviewed,
        "approval_rate": round(
            counts.get("positive", 0) / max(counts.get("positive", 0) + counts.get("negative", 0), 1) * 100,
            1,
        ),
    }


# ---------------------------------------------------------------------------
# Pinecone promotion
# ---------------------------------------------------------------------------

async def _safe_promote(feedback_id: str, feedback: dict, correction: str):
    """Safe wrapper that logs exceptions instead of swallowing them."""
    try:
        await _promote_to_pinecone(feedback_id, feedback, correction)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"[admin] Pinecone promotion task failed: {e}", exc_info=True)


async def _promote_to_pinecone(feedback_id: str, feedback: dict, correction: str):
    """Push a verified correction to Pinecone global_knowledge namespace."""
    try:
        from app.services.rag import _get_pinecone_index

        index = _get_pinecone_index()
        if not index:
            logger.warning("[admin] Pinecone not configured — skipping promotion")
            return

        question = feedback.get("question", "")
        wrong_answer = (feedback.get("answer", "") or "")[:200]

        # Format as a correction that RAG will surface for similar questions
        correction_text = (
            f"## Verified Correction\n\n"
            f"Question: {question}\n\n"
            f"A previous AI response was incorrect: \"{wrong_answer}...\"\n\n"
            f"**Correct answer:** {correction}\n\n"
            f"Source: Verified by Arrival team from user feedback."
        )

        record = {
            "_id": f"correction_{feedback_id}",
            "text": correction_text,
            "document_id": f"correction_{feedback_id}",
            "user_id": "system",
            "filename": "verified_corrections",
            "chunk_index": 0,
        }

        await asyncio.to_thread(
            index.upsert_records,
            namespace="global_knowledge",
            records=[record],
        )
        logger.info(f"[admin] Promoted correction to Pinecone: {feedback_id}")

    except Exception as e:
        logger.warning(f"[admin] Pinecone promotion failed: {e}")


# ---------------------------------------------------------------------------
# Auto-knowledge generation from positive feedback
# ---------------------------------------------------------------------------

@router.post("/admin/knowledge/generate")
async def generate_knowledge(
    secret: str = Query(""),
    limit: int = Query(20, le=50),
):
    """Auto-generate knowledge base entries from positively-rated Q&A pairs.

    Finds responses that got thumbs-up but had NO RAG context (Claude answered
    from general knowledge). These are candidates for indexing so RAG catches
    them next time (faster, more consistent).
    """
    _check_admin(secret)

    promoted = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Find positive feedback where source doesn't indicate RAG usage
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/feedback",
            headers=_supa_headers(),
            params={
                "rating": "eq.positive",
                "promoted_to_knowledge": "eq.false",
                "order": "created_at.desc",
                "limit": str(limit * 2),  # fetch extra to filter
                "select": "id,question,answer,source",
            },
        )
        resp.raise_for_status()
        candidates = resp.json()

        if not candidates:
            return {"success": True, "promoted": 0, "message": "No candidates found"}

        # Filter: only keep Q&A pairs where the source doesn't mention uploaded docs
        # (i.e., Claude answered from general knowledge, not RAG)
        qa_pairs = []
        for fb in candidates:
            source = (fb.get("source") or "").lower()
            # Skip if source indicates RAG was used (contains filenames)
            if ".pdf" in source or ".md" in source or ".txt" in source or "+" in source:
                continue
            # Skip very short answers (probably greetings)
            if len(fb.get("answer", "")) < 50:
                continue
            qa_pairs.append(fb)
            if len(qa_pairs) >= limit:
                break

        if not qa_pairs:
            return {"success": True, "promoted": 0, "message": "No pure-Claude answers with positive feedback"}

        # Generate Pinecone chunks from validated Q&A pairs
        try:
            from app.services.rag import _get_pinecone_index

            index = _get_pinecone_index()
            if not index:
                return {"success": False, "message": "Pinecone not configured"}

            records = []
            promoted_ids = []
            for fb in qa_pairs:
                record = {
                    "_id": f"auto_qa_{fb['id']}",
                    "text": (
                        f"## Validated Q&A\n\n"
                        f"Q: {fb['question']}\n\n"
                        f"A: {fb['answer']}\n\n"
                        f"Source: Auto-generated from positive user feedback."
                    ),
                    "document_id": f"auto_qa_{fb['id']}",
                    "user_id": "system",
                    "filename": "auto_generated_qa",
                    "chunk_index": 0,
                    "auto_generated": True,
                }
                records.append(record)
                promoted_ids.append(fb["id"])

            # Batch upsert to Pinecone
            await asyncio.to_thread(
                index.upsert_records,
                namespace="global_knowledge",
                records=records,
            )
            promoted = len(records)

            # Mark as promoted in Supabase
            for fb_id in promoted_ids:
                await client.patch(
                    f"{config.SUPABASE_URL}/rest/v1/feedback",
                    headers=_supa_headers(),
                    params={"id": f"eq.{fb_id}"},
                    json={"promoted_to_knowledge": True},
                )

            logger.info(f"[admin] Auto-generated {promoted} knowledge entries from positive feedback")

        except Exception as e:
            logger.error(f"[admin] Knowledge generation failed: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    return {"success": True, "promoted": promoted}
