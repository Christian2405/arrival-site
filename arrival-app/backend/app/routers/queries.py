"""
Queries router — GET /api/queries
Returns query history for team activity dashboards.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.supabase import get_team_queries

router = APIRouter()


class QueriesResponse(BaseModel):
    queries: list[dict]
    total: int


@router.get("/queries", response_model=QueriesResponse)
async def list_queries(
    request: Request,
    team_id: str = Query(..., description="Team ID to get queries for"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List recent queries for a team — powers the Team Activity feed.
    Requires authentication; RLS ensures user is a team member.
    """
    try:
        user = await get_current_user(request)
        queries = await get_team_queries(
            team_id=team_id,
            user_token=user["token"],
            limit=limit,
        )
        return QueriesResponse(queries=queries, total=len(queries))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query list failed: {str(e)}")
