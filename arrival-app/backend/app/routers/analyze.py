"""
Frame analysis router — POST /api/analyze-frame
Job Mode: analyzes camera frames and returns alerts only when notable.
Business tier only (enforced on frontend).
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.anthropic import analyze_frame

router = APIRouter()


class FrameRequest(BaseModel):
    image_base64: str


class FrameResponse(BaseModel):
    alert: bool
    message: str | None = None
    severity: str | None = None  # "warning" or "critical"


@router.post("/analyze-frame", response_model=FrameResponse)
async def analyze(request: FrameRequest, req: Request):
    """
    Analyze a camera frame for Job Mode.
    Returns alert=False if nothing notable, or alert=True with message + severity.
    """
    try:
        # Auth required — this is a paid feature
        user = await get_current_user(req)
        result = await analyze_frame(request.image_base64)
        return FrameResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame analysis failed: {str(e)}")
