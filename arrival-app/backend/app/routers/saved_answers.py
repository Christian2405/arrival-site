"""
Saved Answers router — POST, GET, DELETE /api/saved-answers
Syncs bookmarked AI responses to Supabase for cross-device persistence.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app import config
import httpx

router = APIRouter()


class SaveAnswerRequest(BaseModel):
    question: str
    answer: str
    source: str | None = None
    confidence: str | None = None
    trade: str = "HVAC"


class SavedAnswerResponse(BaseModel):
    id: str
    question: str
    answer: str
    source: str | None = None
    confidence: str | None = None
    trade: str
    saved_at: str


class SavedAnswersListResponse(BaseModel):
    answers: list[dict]


class DeleteResponse(BaseModel):
    success: bool


def _db_headers(user_token: str) -> dict:
    return {
        "apikey": config.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


@router.post("/saved-answers", response_model=SavedAnswerResponse)
async def save_answer(body: SaveAnswerRequest, request: Request):
    """Save a bookmarked AI response."""
    try:
        user = await get_current_user(request)
        user_id = user["user_id"]
        user_token = user["token"]

        row = {
            "user_id": user_id,
            "question": body.question,
            "answer": body.answer,
            "source": body.source,
            "confidence": body.confidence,
            "trade": body.trade,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{config.SUPABASE_URL}/rest/v1/saved_answers",
                headers=_db_headers(user_token),
                json=row,
            )
            resp.raise_for_status()
            inserted = resp.json()

        record = inserted[0] if isinstance(inserted, list) else inserted
        return SavedAnswerResponse(
            id=record["id"],
            question=record["question"],
            answer=record["answer"],
            source=record.get("source"),
            confidence=record.get("confidence"),
            trade=record.get("trade", "HVAC"),
            saved_at=record.get("saved_at", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")


@router.get("/saved-answers", response_model=SavedAnswersListResponse)
async def list_saved_answers(request: Request):
    """List all saved answers for the authenticated user."""
    try:
        user = await get_current_user(request)
        user_token = user["token"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/saved_answers",
                headers=_db_headers(user_token),
                params={
                    "select": "*",
                    "order": "saved_at.desc",
                    "limit": "200",
                },
            )
            resp.raise_for_status()
            rows = resp.json()

        return SavedAnswersListResponse(answers=rows)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


@router.delete("/saved-answers/{answer_id}", response_model=DeleteResponse)
async def delete_saved_answer(answer_id: str, request: Request):
    """Delete a saved answer by ID."""
    try:
        user = await get_current_user(request)
        user_token = user["token"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{config.SUPABASE_URL}/rest/v1/saved_answers",
                headers=_db_headers(user_token),
                params={"id": f"eq.{answer_id}"},
            )
            resp.raise_for_status()

        return DeleteResponse(success=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
