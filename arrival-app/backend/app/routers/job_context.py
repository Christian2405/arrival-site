"""
Job Context router — POST/GET/DELETE /api/job-context
Allows the frontend to set, get, and clear the equipment context for Job Mode.
"""

import logging
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.job_context import (
    set_job_context,
    get_job_context,
    clear_job_context,
    EQUIPMENT_TYPES,
    COMMON_BRANDS,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class JobContextRequest(BaseModel):
    equipment_type: str
    brand: str | None = None
    model: str | None = None


class JobContextResponse(BaseModel):
    equipment_type: str
    brand: str | None = None
    model: str | None = None


class JobContextOptionsResponse(BaseModel):
    equipment_types: list[str]
    brands: list[str]


@router.post("/job-context", response_model=JobContextResponse)
async def set_context(request: JobContextRequest, req: Request):
    """Set the equipment context for the current job mode session."""
    user = await get_current_user(req)
    user_id = user["user_id"]

    if request.equipment_type not in EQUIPMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid equipment type. Must be one of: {', '.join(EQUIPMENT_TYPES)}",
        )

    ctx = set_job_context(
        user_id=user_id,
        equipment_type=request.equipment_type,
        brand=request.brand,
        model=request.model,
    )

    return JobContextResponse(
        equipment_type=ctx["equipment_type"],
        brand=ctx.get("brand"),
        model=ctx.get("model"),
    )


@router.get("/job-context", response_model=JobContextResponse | None)
async def get_context(req: Request):
    """Get the current equipment context for the user."""
    user = await get_current_user(req)
    user_id = user["user_id"]

    ctx = get_job_context(user_id)
    if not ctx:
        return None

    return JobContextResponse(
        equipment_type=ctx["equipment_type"],
        brand=ctx.get("brand"),
        model=ctx.get("model"),
    )


@router.delete("/job-context")
async def delete_context(req: Request):
    """Clear the equipment context for the user."""
    user = await get_current_user(req)
    user_id = user["user_id"]

    cleared = clear_job_context(user_id)
    return {"cleared": cleared}


@router.get("/job-context/options", response_model=JobContextOptionsResponse)
async def get_options():
    """Get available equipment types and brands for the quick-set UI."""
    return JobContextOptionsResponse(
        equipment_types=EQUIPMENT_TYPES,
        brands=COMMON_BRANDS,
    )
