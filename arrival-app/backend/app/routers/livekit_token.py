"""
LiveKit token generation endpoint.
Creates access tokens for mobile clients to join LiveKit voice rooms.
The LiveKit agent auto-joins when a participant connects.
"""

import datetime
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from livekit import api

from app import config
from app.middleware.auth import decode_jwt_token
from app.services.frame_store import store_frame, get_frame, get_frame_age

logger = logging.getLogger(__name__)

router = APIRouter()


class TokenRequest(BaseModel):
    mode: str = "job"  # "job" or "default"


class TokenResponse(BaseModel):
    token: str
    ws_url: str
    room_name: str


@router.get("/livekit-status")
async def livekit_status():
    """Diagnostic: check LiveKit config is loaded (no auth required)."""
    key = config.LIVEKIT_API_KEY or ""
    secret = config.LIVEKIT_API_SECRET or ""
    url = config.LIVEKIT_URL or ""
    return {
        "configured": bool(key and secret and url),
        "key_prefix": key[:5] + "***" if len(key) >= 5 else "NOT_SET",
        "key_len": len(key),
        "url": url,
        "secret_len": len(secret),
    }


@router.get("/livekit-debug")
async def livekit_debug():
    """Diagnostic: check LiveKit Cloud rooms and agent worker status."""
    import subprocess
    if not config.LIVEKIT_URL or not config.LIVEKIT_API_KEY or not config.LIVEKIT_API_SECRET:
        return {"configured": False, "error": "LiveKit env vars not set"}

    info = {
        "configured": True,
        "url": config.LIVEKIT_URL,
        "key_prefix": config.LIVEKIT_API_KEY[:5] + "***",
    }

    # Check if agent process is alive on this server
    try:
        result = subprocess.run(
            ["pgrep", "-f", "livekit_agent.agent"],
            capture_output=True, text=True, timeout=5
        )
        agent_pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        info["agent_process_running"] = len(agent_pids) > 0
        info["agent_pids"] = agent_pids
    except Exception as e:
        info["agent_process_check_error"] = str(e)

    # Try to start agent directly and capture the error
    try:
        result = subprocess.run(
            ["python", "-c", "import livekit_agent.agent; print('IMPORT OK')"],
            capture_output=True, text=True, timeout=15
        )
        info["agent_import_stdout"] = result.stdout[-500:] if result.stdout else ""
        info["agent_import_stderr"] = result.stderr[-500:] if result.stderr else ""
        info["agent_import_returncode"] = result.returncode
    except Exception as e:
        info["agent_import_error"] = str(e)

    # Use LiveKit Server API to check Cloud status
    try:
        lk = api.LiveKitAPI(
            config.LIVEKIT_URL,
            api_key=config.LIVEKIT_API_KEY,
            api_secret=config.LIVEKIT_API_SECRET,
        )
    except Exception as e:
        info["api_init_error"] = f"{type(e).__name__}: {e}"
        return info

    # List active rooms
    try:
        rooms_resp = await lk.room.list_rooms(api.ListRoomsRequest())
        rooms_info = []
        for r in rooms_resp.rooms:
            room_data = {"name": r.name, "num_participants": r.num_participants}
            # Try to list participants in each room
            try:
                parts_resp = await lk.room.list_participants(
                    api.ListParticipantsRequest(room=r.name)
                )
                room_data["participants"] = [
                    {"identity": p.identity, "name": p.name}
                    for p in parts_resp.participants
                ]
            except Exception:
                pass
            rooms_info.append(room_data)

        info["rooms"] = rooms_info
        info["room_count"] = len(rooms_info)
    except Exception as e:
        info["rooms_error"] = f"{type(e).__name__}: {e}"

    try:
        await lk.aclose()
    except Exception:
        pass

    return info


@router.post("/livekit-token", response_model=TokenResponse)
async def create_livekit_token(req: TokenRequest, request: Request):
    """Generate a LiveKit room token for the authenticated user."""
    # --- Auth ---
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")

    jwt_token = auth_header.replace("Bearer ", "")
    try:
        payload = await decode_jwt_token(jwt_token)
    except (ValueError, Exception) as e:
        logger.warning(f"[livekit-token] JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="No user ID in token")

    # --- Check LiveKit config ---
    if not config.LIVEKIT_API_KEY or not config.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail="LiveKit not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET.",
        )

    logger.info(f"[livekit-token] Config: key={config.LIVEKIT_API_KEY[:5]}*** url={config.LIVEKIT_URL}")

    # --- Room name encodes mode + user for the agent to parse ---
    short_id = user_id[:8].replace("-", "")
    room_name = f"arrival_{req.mode}_{short_id}_{uuid.uuid4().hex[:6]}"

    # --- Participant metadata — agent reads this for full user context ---
    participant_metadata = json.dumps({
        "user_id": user_id,
        "mode": req.mode,
    })

    # --- Generate token ---
    token = (
        api.AccessToken(config.LIVEKIT_API_KEY, config.LIVEKIT_API_SECRET)
        .with_identity(user_id)
        .with_name(f"User {short_id}")
        .with_ttl(datetime.timedelta(hours=8))  # Full work shift
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
        .with_metadata(participant_metadata)
        .to_jwt()
    )

    logger.info(f"[livekit-token] Generated token for user={short_id} room={room_name} mode={req.mode}")

    # NOTE: Do NOT explicitly dispatch agents here — LiveKit auto-dispatch
    # handles it. Explicit dispatch + auto-dispatch = duplicate agents.

    return TokenResponse(
        token=token,
        ws_url=config.LIVEKIT_URL,
        room_name=room_name,
    )


class FrameUpload(BaseModel):
    room_name: str
    frame: str  # base64 JPEG


@router.post("/livekit-frame")
async def upload_frame(req: FrameUpload, request: Request):
    """Upload a camera frame for the agent to analyze.
    Uses HTTP instead of WebRTC data channel for reliability."""
    # Light auth check — just verify bearer token exists
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")

    store_frame(req.room_name, req.frame)
    logger.info(f"[livekit-frame] Stored frame for room={req.room_name} ({len(req.frame)} chars)")
    return {"ok": True}


@router.get("/livekit-frame/{room_name}")
async def get_frame_api(room_name: str):
    """Get the latest camera frame for a room.
    Used by the LiveKit agent (separate process) to fetch frames via HTTP.
    This is more reliable than file-based sharing across process boundaries."""
    frame = get_frame(room_name)
    if not frame:
        raise HTTPException(status_code=404, detail="No frame available")
    age = get_frame_age(room_name)
    return {"frame": frame, "age": round(age, 1) if age is not None else None}


class AnalyzeRequest(BaseModel):
    room_name: str
    question: str = "What do you see?"
    frame: str | None = None  # Optional inline frame (base64 JPEG) — bypasses frame store


@router.post("/livekit-analyze")
async def livekit_analyze_frame(req: AnalyzeRequest):
    """Analyze a camera frame using Claude Vision.
    Accepts an inline frame (from frontend) or reads from the frame store.
    Called by the LiveKit agent or the mobile frontend.
    NOTE: renamed from /analyze-frame to avoid conflict with analyze.py router."""
    import anthropic as anthropic_sdk

    # Use inline frame if provided, otherwise read from store
    frame = req.frame
    if not frame:
        frame = get_frame(req.room_name)
    if not frame:
        age = get_frame_age(req.room_name)
        raise HTTPException(
            status_code=404,
            detail=f"No frame for room {req.room_name}. age={age}"
        )

    logger.info(f"[analyze-frame] Analyzing frame for room={req.room_name} ({len(frame)} chars)")

    try:
        client = anthropic_sdk.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=config.ANTHROPIC_VOICE_MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": frame,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "You're a 50-year trade veteran looking at this through a tech's phone camera. "
                            f"{req.question}. Be specific and practical, 1-3 sentences. "
                            "If you can read any model numbers, brands, or error codes, mention them."
                        ),
                    },
                ],
            }],
        )
        result_text = response.content[0].text
        logger.info(f"[analyze-frame] Result: {result_text[:100]}...")
        return {"analysis": result_text, "frame_size": len(frame)}
    except Exception as e:
        logger.error(f"[analyze-frame] Vision API failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {e}")


@router.get("/livekit-frame-debug/{room_name}")
async def frame_debug(room_name: str):
    """Diagnostic: check if a frame exists in the file store for a room."""
    import os
    frame = get_frame(room_name)
    age = get_frame_age(room_name)

    frame_dir = "/tmp/arrival_frames"
    files = []
    try:
        files = os.listdir(frame_dir)
    except OSError:
        pass

    return {
        "room_name": room_name,
        "frame_found": frame is not None,
        "frame_size": len(frame) if frame else 0,
        "frame_age_seconds": round(age, 1) if age is not None else None,
        "all_frame_files": files,
        "frame_dir": frame_dir,
    }
