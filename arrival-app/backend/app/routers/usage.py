"""
Usage router — GET /api/usage
Returns the authenticated user's current usage stats and tier limits.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.middleware.auth import get_current_user
from app.services.usage import (
    get_user_plan,
    get_tier_limits,
    get_daily_query_count,
    get_document_count,
    get_job_mode_seconds_today,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/usage")
async def get_usage(request: Request):
    """
    Return the current user's usage stats and limits.
    Skips expensive count queries for unlimited tiers.
    """
    try:
        user = await get_current_user(request)
        user_id = user["user_id"]

        plan = await get_user_plan(user_id)
        limits = get_tier_limits(plan)

        max_queries = limits["max_queries_per_day"]
        max_docs = limits["max_documents"]

        # Skip count queries for unlimited tiers
        queries_today = 0
        if max_queries < 9999:
            queries_today = await get_daily_query_count(user_id)

        documents_count = 0
        if max_docs < 9999:
            documents_count = await get_document_count(user_id)

        job_minutes = limits.get("job_mode_minutes", -1)

        # Get job mode time used today (skip for unlimited)
        job_seconds_used = 0
        if job_minutes > 0:
            job_seconds_used = await get_job_mode_seconds_today(user_id)

        return {
            "plan": plan,
            "queries_today": queries_today,
            "query_limit": -1 if max_queries >= 9999 else max_queries,
            "documents_count": documents_count,
            "document_limit": -1 if max_docs >= 9999 else max_docs,
            "job_mode": limits["job_mode"],
            "job_mode_minutes": job_minutes,
            "job_seconds_used_today": job_seconds_used,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[usage] Failed to get usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage data")
