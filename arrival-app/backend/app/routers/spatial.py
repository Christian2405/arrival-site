"""
Arrival Backend — Spatial Intelligence Endpoints
Debug/admin endpoints for spatial data capture.
"""

from fastapi import APIRouter, HTTPException, Request
import httpx

from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from app.middleware.auth import decode_jwt_token
from app.services.s3 import get_presigned_url

router = APIRouter(prefix="/api/spatial", tags=["spatial"])


async def _require_auth(request: Request) -> str:
    """Require valid JWT. Returns user_id."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    try:
        payload = await decode_jwt_token(auth.replace("Bearer ", ""))
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload.get("sub", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

_SERVICE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


@router.get("/sessions")
async def list_sessions(request: Request, limit: int = 20):
    """List recent spatial sessions."""
    await _require_auth(request)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/spatial_sessions?order=created_at.desc&limit={limit}",
            headers=_SERVICE_HEADERS,
            timeout=10,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/clips/{session_id}")
async def list_clips(request: Request, session_id: str):
    """List clips for a session."""
    await _require_auth(request)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/spatial_clips?session_id=eq.{session_id}&order=created_at.desc",
            headers=_SERVICE_HEADERS,
            timeout=10,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/clip/{clip_id}/url")
async def get_clip_url(request: Request, clip_id: str):
    """Get a presigned S3 URL for clip playback."""
    await _require_auth(request)
    # Get the clip's s3_key from Supabase
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/spatial_clips?id=eq.{clip_id}&select=s3_key,status",
            headers=_SERVICE_HEADERS,
            timeout=10,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    clips = resp.json()
    if not clips:
        raise HTTPException(status_code=404, detail="Clip not found")

    clip = clips[0]
    if clip["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Clip not ready (status: {clip['status']})")

    url = await get_presigned_url(clip["s3_key"])
    return {"url": url, "s3_key": clip["s3_key"]}


@router.get("/stats")
async def get_stats(request: Request):
    """Get basic spatial capture stats."""
    await _require_auth(request)
    async with httpx.AsyncClient() as client:
        sessions_resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/spatial_sessions?select=id",
            headers={**_SERVICE_HEADERS, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
            timeout=10,
        )
        clips_resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/spatial_clips?status=eq.ready&select=id",
            headers={**_SERVICE_HEADERS, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
            timeout=10,
        )

    session_count = sessions_resp.headers.get("content-range", "*/0").split("/")[-1]
    clip_count = clips_resp.headers.get("content-range", "*/0").split("/")[-1]

    return {
        "total_sessions": int(session_count) if session_count != "*" else 0,
        "total_clips_ready": int(clip_count) if clip_count != "*" else 0,
    }
