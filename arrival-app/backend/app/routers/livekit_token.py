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
    if not config.LIVEKIT_URL or not config.LIVEKIT_API_KEY or not config.LIVEKIT_API_SECRET:
        return {"configured": False, "error": "LiveKit env vars not set"}

    info = {
        "configured": True,
        "url": config.LIVEKIT_URL,
        "key_prefix": config.LIVEKIT_API_KEY[:5] + "***",
    }

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

    # Pre-create the room and try explicit agent dispatch
    # This ensures the room exists before the client joins, and explicitly
    # dispatches the agent worker (in case auto-dispatch isn't working)
    try:
        lk = api.LiveKitAPI(
            config.LIVEKIT_URL,
            api_key=config.LIVEKIT_API_KEY,
            api_secret=config.LIVEKIT_API_SECRET,
        )
        # Create the room before the client joins
        await lk.room.create_room(api.CreateRoomRequest(
            name=room_name,
            empty_timeout=300,  # 5 min empty timeout
            max_participants=3,  # user + agent + buffer
        ))
        logger.info(f"[livekit-token] ✓ Pre-created room: {room_name}")

        # Try explicit agent dispatch (belt + suspenders with auto-dispatch)
        try:
            await lk.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(room=room_name)
            )
            logger.info(f"[livekit-token] ✓ Explicit agent dispatch: {room_name}")
        except Exception as de:
            logger.info(f"[livekit-token] Agent dispatch API: {de} (auto-dispatch expected)")

        await lk.aclose()
    except Exception as e:
        # Room pre-creation is optional — don't block token generation
        logger.warning(f"[livekit-token] Room pre-creation (non-fatal): {e}")

    return TokenResponse(
        token=token,
        ws_url=config.LIVEKIT_URL,
        room_name=room_name,
    )
