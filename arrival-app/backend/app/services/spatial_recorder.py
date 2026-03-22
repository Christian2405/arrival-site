"""
Arrival Backend — Spatial Intelligence Recorder
Records video clips from WebRTC frames, encodes to MP4 via ffmpeg,
uploads to S3, and logs metadata to Supabase.
"""

import asyncio
import base64
import logging
import uuid
from datetime import datetime

import httpx

from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY
from app.services.s3 import upload_clip, build_s3_key

logger = logging.getLogger("arrival.spatial")

# Supabase service role headers (same pattern as supabase.py)
_SERVICE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


class SpatialRecorder:
    """Records video clips from agent frame data for spatial intelligence dataset."""

    def __init__(self):
        self._session_id: str | None = None
        self._room_name: str = ""
        self._user_id: str = ""
        self._consent: bool = False
        self._recording: bool = False
        self._clip_count: int = 0

    async def start_session(
        self,
        room_name: str,
        user_id: str,
        team_id: str | None,
        trade: str | None,
        equipment: dict | None,
        consent: bool = False,
    ) -> str | None:
        """Create a spatial session in Supabase. Returns session ID."""
        self._room_name = room_name
        self._user_id = user_id
        self._consent = consent

        if not consent:
            logger.info(f"Spatial recording disabled for {room_name} (no consent)")
            return None

        equip = equipment or {}
        payload = {
            "room_name": room_name,
            "user_id": user_id,
            "team_id": team_id,
            "trade": trade,
            "equipment_type": equip.get("type"),
            "equipment_brand": equip.get("brand"),
            "equipment_model": equip.get("model"),
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SUPABASE_URL}/rest/v1/spatial_sessions",
                    headers=_SERVICE_HEADERS,
                    json=payload,
                    timeout=10,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    self._session_id = data[0]["id"] if isinstance(data, list) else data["id"]
                    logger.info(f"Spatial session started: {self._session_id}")
                    return self._session_id
                else:
                    logger.error(f"Failed to create spatial session: {resp.status_code} {resp.text}")
                    return None
        except Exception as e:
            logger.error(f"Error creating spatial session: {e}")
            return None

    async def end_session(self):
        """Mark session as ended and update clip count."""
        if not self._session_id:
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/spatial_sessions?id=eq.{self._session_id}",
                    headers=_SERVICE_HEADERS,
                    json={
                        "ended_at": datetime.utcnow().isoformat(),
                        "clip_count": self._clip_count,
                    },
                    timeout=10,
                )
            logger.info(f"Spatial session ended: {self._session_id} ({self._clip_count} clips)")
        except Exception as e:
            logger.error(f"Error ending spatial session: {e}")

    async def trigger_recording(
        self,
        trigger_type: str,
        trigger_text: str,
        agent,
        monitor_state: str = "",
    ):
        """Trigger a clip recording. Skips if no consent or already recording."""
        if not self._consent:
            return
        if not self._session_id:
            return
        if self._recording:
            logger.debug("Skipping recording trigger — already recording")
            return
        if not hasattr(agent, "_latest_frame") or not agent._latest_frame:
            logger.debug("Skipping recording trigger — no frame available")
            return

        # Fire and forget
        asyncio.ensure_future(
            self._record_clip(trigger_type, trigger_text, agent, monitor_state)
        )

    async def _record_clip(
        self,
        trigger_type: str,
        trigger_text: str,
        agent,
        monitor_state: str = "",
        duration: int = 20,
    ):
        """Record a clip: collect frames, encode MP4, upload to S3, log to Supabase."""
        clip_id = str(uuid.uuid4())
        s3_key = build_s3_key(self._session_id, clip_id)
        self._recording = True

        try:
            # 1. Create clip record in Supabase
            clip_row = {
                "id": clip_id,
                "session_id": self._session_id,
                "s3_key": s3_key,
                "trigger_type": trigger_type,
                "trigger_text": (trigger_text or "")[:2000],  # Truncate long text
                "monitor_state": monitor_state,
                "status": "recording",
                "resolution": "720x1280",
            }
            await self._insert_clip(clip_row)
            logger.info(f"Recording clip {clip_id} ({trigger_type}: {trigger_text[:80] if trigger_text else ''})")

            # 2. Collect frames for `duration` seconds at ~2fps
            frames: list[bytes] = []
            end_time = asyncio.get_event_loop().time() + duration

            while asyncio.get_event_loop().time() < end_time:
                try:
                    frame_b64 = getattr(agent, "_latest_frame", None)
                    if frame_b64:
                        frame_bytes = base64.b64decode(frame_b64)
                        frames.append(frame_bytes)
                except Exception:
                    pass  # Skip bad frames
                await asyncio.sleep(0.5)

            if not frames:
                await self._update_clip_status(clip_id, "failed", error="No frames captured")
                return

            logger.info(f"Clip {clip_id}: collected {len(frames)} frames")

            # 3. Encode to MP4 via ffmpeg
            await self._update_clip_status(clip_id, "encoding")
            mp4_data = await self._encode_mp4(frames, fps=2)

            if not mp4_data:
                await self._update_clip_status(clip_id, "failed", error="ffmpeg encoding failed")
                return

            logger.info(f"Clip {clip_id}: encoded to {len(mp4_data)} bytes MP4")

            # 4. Upload to S3
            await self._update_clip_status(clip_id, "uploading")
            await upload_clip(s3_key, mp4_data)

            # 5. Mark as ready
            await self._update_clip_final(
                clip_id,
                status="ready",
                file_size=len(mp4_data),
                frame_count=len(frames),
                duration_seconds=len(frames) / 2.0,  # 2fps
            )
            self._clip_count += 1
            logger.info(f"Clip {clip_id} ready: s3://{s3_key} ({len(mp4_data)} bytes, {len(frames)} frames)")

        except Exception as e:
            logger.error(f"Clip {clip_id} failed: {e}")
            try:
                await self._update_clip_status(clip_id, "failed", error=str(e)[:500])
            except Exception:
                pass
        finally:
            self._recording = False

    async def _encode_mp4(self, frames: list[bytes], fps: int = 2) -> bytes | None:
        """Encode JPEG frames to MP4 via ffmpeg subprocess."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-f", "image2pipe",
                "-framerate", str(fps),
                "-i", "pipe:0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-f", "mp4",
                "-y",
                "pipe:1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Write all JPEG frames to stdin
            input_data = b"".join(frames)
            stdout, stderr = await proc.communicate(input=input_data)

            if proc.returncode != 0:
                logger.error(f"ffmpeg failed (rc={proc.returncode}): {stderr.decode()[:500]}")
                return None

            return stdout

        except FileNotFoundError:
            logger.error("ffmpeg not found — install ffmpeg to enable spatial recording")
            return None
        except Exception as e:
            logger.error(f"ffmpeg error: {e}")
            return None

    # --- Supabase helpers ---

    async def _insert_clip(self, data: dict):
        """Insert a clip row."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/spatial_clips",
                    headers=_SERVICE_HEADERS,
                    json=data,
                    timeout=10,
                )
        except Exception as e:
            logger.error(f"Failed to insert clip: {e}")

    async def _update_clip_status(self, clip_id: str, status: str, error: str = ""):
        """Update clip status."""
        payload = {"status": status}
        if error:
            payload["error_message"] = error
        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/spatial_clips?id=eq.{clip_id}",
                    headers=_SERVICE_HEADERS,
                    json=payload,
                    timeout=10,
                )
        except Exception as e:
            logger.error(f"Failed to update clip status: {e}")

    async def _update_clip_final(
        self, clip_id: str, status: str, file_size: int, frame_count: int, duration_seconds: float
    ):
        """Final update with all metadata."""
        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/spatial_clips?id=eq.{clip_id}",
                    headers=_SERVICE_HEADERS,
                    json={
                        "status": status,
                        "file_size_bytes": file_size,
                        "frame_count": frame_count,
                        "duration_seconds": duration_seconds,
                    },
                    timeout=10,
                )
        except Exception as e:
            logger.error(f"Failed to update clip final: {e}")
