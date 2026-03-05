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


@router.post("/livekit-token", response_model=TokenResponse)
async def create_livekit_token(req: TokenRequest, request: Request):
    """Generate a LiveKit room token for the authenticated user."""
    # --- Auth ---
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")

    jwt_token = auth_header.replace("Bearer ", "")
    payload = await decode_jwt_token(jwt_token)
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

    return TokenResponse(
        token=token,
        ws_url=config.LIVEKIT_URL,
        room_name=room_name,
    )
