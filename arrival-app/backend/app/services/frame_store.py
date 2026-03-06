"""
Frame Store — simple in-memory store for camera frames.
The mobile app POSTs frames here, and the LiveKit agent reads them.
This bypasses unreliable WebRTC data channels for large image payloads.

TTL: Frames expire after 60 seconds (stale frames are useless).
"""

import time
import logging

logger = logging.getLogger(__name__)

# In-memory store: room_name -> { frame: base64_str, updated_at: float }
_frames: dict[str, dict] = {}

FRAME_TTL = 60  # seconds


def store_frame(room_name: str, frame_b64: str):
    """Store a camera frame for a room."""
    _frames[room_name] = {
        "frame": frame_b64,
        "updated_at": time.time(),
    }
    # Prune old frames occasionally
    if len(_frames) > 50:
        _prune()


def get_frame(room_name: str) -> str | None:
    """Get the latest camera frame for a room. Returns None if expired or missing."""
    entry = _frames.get(room_name)
    if not entry:
        return None
    if time.time() - entry["updated_at"] > FRAME_TTL:
        del _frames[room_name]
        return None
    return entry["frame"]


def get_frame_age(room_name: str) -> float | None:
    """Get the age of the latest frame in seconds. None if no frame."""
    entry = _frames.get(room_name)
    if not entry:
        return None
    return time.time() - entry["updated_at"]


def _prune():
    """Remove expired frames."""
    now = time.time()
    expired = [k for k, v in _frames.items() if now - v["updated_at"] > FRAME_TTL]
    for k in expired:
        del _frames[k]
