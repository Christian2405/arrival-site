"""
Frame Store — file-based store for camera frames.
The mobile app POSTs frames to FastAPI, and the LiveKit agent reads them.
Uses /tmp filesystem so BOTH processes (FastAPI + agent) can access frames.

Why files, not in-memory: FastAPI and the LiveKit agent run as separate
processes (start.sh). An in-memory dict only lives in the process that
wrote it — the other process sees an empty dict. /tmp is shared.

TTL: Frames expire after 60 seconds (stale frames are useless).
"""

import json
import os
import re
import time
import logging

logger = logging.getLogger(__name__)

FRAME_DIR = "/tmp/arrival_frames"
FRAME_TTL = 60  # seconds


def _safe_filename(room_name: str) -> str:
    """Sanitize room name for use as filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", room_name)


def _ensure_dir():
    """Create frame directory if it doesn't exist."""
    os.makedirs(FRAME_DIR, exist_ok=True)


def store_frame(room_name: str, frame_b64: str):
    """Store a camera frame for a room. Atomic write via rename."""
    _ensure_dir()
    safe_name = _safe_filename(room_name)
    path = os.path.join(FRAME_DIR, f"{safe_name}.json")
    tmp_path = path + ".tmp"

    data = json.dumps({"frame": frame_b64, "updated_at": time.time()})

    try:
        with open(tmp_path, "w") as f:
            f.write(data)
        os.replace(tmp_path, path)  # Atomic on Linux
    except OSError as e:
        logger.warning(f"[frame-store] Failed to write frame for {room_name}: {e}")
        return

    # Prune old files occasionally
    _prune()


def get_frame(room_name: str) -> str | None:
    """Get the latest camera frame for a room. Returns None if expired or missing."""
    safe_name = _safe_filename(room_name)
    path = os.path.join(FRAME_DIR, f"{safe_name}.json")

    try:
        with open(path, "r") as f:
            data = json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    if time.time() - data["updated_at"] > FRAME_TTL:
        try:
            os.remove(path)
        except OSError:
            pass
        return None

    return data["frame"]


def get_frame_age(room_name: str) -> float | None:
    """Get the age of the latest frame in seconds. None if no frame."""
    safe_name = _safe_filename(room_name)
    path = os.path.join(FRAME_DIR, f"{safe_name}.json")

    try:
        with open(path, "r") as f:
            data = json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    return time.time() - data["updated_at"]


def _prune():
    """Remove expired frame files."""
    try:
        now = time.time()
        for fname in os.listdir(FRAME_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(FRAME_DIR, fname)
            try:
                with open(fpath, "r") as f:
                    data = json.loads(f.read())
                if now - data["updated_at"] > FRAME_TTL:
                    os.remove(fpath)
            except (json.JSONDecodeError, OSError, KeyError):
                # Corrupt file — remove it
                try:
                    os.remove(fpath)
                except OSError:
                    pass
    except OSError:
        pass
