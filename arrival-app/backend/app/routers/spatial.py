"""
Arrival Backend — Spatial Intelligence Endpoints
Debug/admin endpoints for spatial data capture.
"""

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx

from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, AWS_S3_BUCKET
from app.middleware.auth import decode_jwt_token
from app.services.s3 import upload_clip, get_presigned_url, build_s3_key

logger = logging.getLogger("arrival.spatial")

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


class VoiceClipRequest(BaseModel):
    frames: list[str]  # base64 JPEG frames
    trigger_text: str = ""
    ai_response: str = ""


@router.post("/voice-clip")
async def create_voice_clip(request: Request, body: VoiceClipRequest):
    """Receive frames from Voice Mode PTT, stitch into MP4, upload to S3.
    Called fire-and-forget from the frontend after each voice query with camera."""
    user_id = await _require_auth(request)

    if len(body.frames) < 2:
        return {"status": "skipped", "reason": "too few frames"}

    # Stitch frames into MP4 via ffmpeg in background
    asyncio.create_task(_stitch_voice_clip(
        user_id=user_id,
        frames=body.frames,
        trigger_text=body.trigger_text,
        ai_response=body.ai_response,
    ))
    return {"status": "processing"}


async def _stitch_voice_clip(
    user_id: str,
    frames: list[str],
    trigger_text: str,
    ai_response: str,
):
    """Background: decode frames, encode MP4 via ffmpeg, upload to S3, log to Supabase."""
    clip_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    s3_key = f"voice_clips/{now.year}/{now.month:02d}/{now.day:02d}/{user_id[:8]}/{clip_id}.mp4"

    try:
        # Decode base64 frames to JPEG bytes
        jpeg_frames = []
        for f in frames:
            try:
                jpeg_frames.append(base64.b64decode(f))
            except Exception:
                continue

        if len(jpeg_frames) < 2:
            return

        # Encode to MP4 via ffmpeg (uses imageio-ffmpeg bundled binary)
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_path,
            "-f", "image2pipe",
            "-framerate", "2",
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-f", "mp4",
            "-y", "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        input_data = b"".join(jpeg_frames)
        stdout, stderr = await proc.communicate(input=input_data)

        if proc.returncode != 0 or not stdout:
            logger.error(f"Voice clip ffmpeg failed: {stderr.decode()[:200]}")
            return

        # Upload to S3
        await upload_clip(s3_key, stdout)

        # Log to Supabase
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/spatial_clips",
                headers=_SERVICE_HEADERS,
                json={
                    "id": clip_id,
                    "s3_key": s3_key,
                    "s3_bucket": AWS_S3_BUCKET,
                    "trigger_type": "voice_query",
                    "trigger_text": trigger_text[:2000],
                    "ai_response": ai_response[:2000],
                    "status": "ready",
                    "resolution": "720x1280",
                    "file_size_bytes": len(stdout),
                    "frame_count": len(jpeg_frames),
                    "duration_seconds": len(jpeg_frames) / 2.0,
                },
                timeout=10,
            )

            # Auto-labels
            labels = [
                {"clip_id": clip_id, "label_type": "semantic", "label_value": trigger_text[:500], "confidence": 1.0},
                {"clip_id": clip_id, "label_type": "meta", "label_value": "voice_mode", "confidence": 1.0},
            ]
            await client.post(
                f"{SUPABASE_URL}/rest/v1/spatial_labels",
                headers=_SERVICE_HEADERS,
                json=labels,
                timeout=10,
            )

        logger.info(f"Voice clip saved: {s3_key} ({len(stdout)} bytes, {len(jpeg_frames)} frames)")

    except Exception as e:
        logger.error(f"Voice clip failed: {e}")
