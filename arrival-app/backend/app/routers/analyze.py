"""
Frame analysis router — POST /api/analyze-frame
Job Mode: analyzes camera frames and returns alerts only when notable.
Business tier only (enforced on frontend).
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.anthropic import analyze_frame
from app.services.job_context import get_job_context

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB raw; base64 is ~1.37x larger


class FrameRequest(BaseModel):
    image_base64: str
    previous_alerts: list[str] = []  # Recent alert messages for session memory


class FrameResponse(BaseModel):
    alert: bool
    message: str | None = None
    severity: str | None = None  # "warning" or "critical"


@router.post("/analyze-frame", response_model=FrameResponse)
async def analyze(request: FrameRequest, req: Request):
    """
    Analyze a camera frame for Job Mode.
    Returns alert=False if nothing notable, or alert=True with message + severity.
    Injects job context (equipment type, brand, model) if set by the user.
    """
    try:
        # Validate image size before processing
        if len(request.image_base64) > MAX_IMAGE_SIZE * 1.37:
            raise HTTPException(status_code=400, detail="Image too large (max 5 MB)")

        # Auth required — this is a paid feature
        user = await get_current_user(req)
        user_id = user["user_id"]

        # Get job context so frame analysis knows what equipment the tech is working on
        job_ctx = get_job_context(user_id)

        result = await analyze_frame(
            request.image_base64,
            job_context=job_ctx,
            previous_alerts=request.previous_alerts or None,
        )
        return FrameResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid request or configuration error")
    except Exception as e:
        logger.error(f"[analyze] Frame analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Frame analysis failed")
