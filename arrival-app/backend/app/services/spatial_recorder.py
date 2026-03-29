"""
Arrival Backend — Spatial Intelligence Recorder
Records video clips from WebRTC frames, encodes to MP4 via ffmpeg,
uploads to S3, and logs metadata to Supabase.
"""

import asyncio
import base64
import logging
import time
import uuid
from datetime import datetime

import httpx

from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from app.services.s3 import upload_clip, build_s3_key

# Informal sequence detection: if same equipment + within this window, auto-link
_INFORMAL_SEQUENCE_WINDOW = 300  # 5 minutes
# Outcome inference: if no follow-up questions for this long, assume fixed
_OUTCOME_INFER_SECONDS = 600  # 10 minutes
# Activity freshness: if scene data older than this, mark as low confidence
_ACTIVITY_STALE_SECONDS = 30

logger = logging.getLogger("arrival.spatial")

# Supabase service role headers (same pattern as supabase.py)
_SERVICE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
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
        # Sequence tracking — groups clips into workflows
        self._current_sequence_id: str | None = None
        self._sequence_order: int = 0
        self._last_clip_id: str | None = None
        # Informal sequence detection
        self._last_equipment_key: str = ""
        self._last_query_time: float = 0
        # Outcome tracking
        self._pending_outcome_sequence_id: str | None = None
        self._pending_outcome_clip_id: str | None = None
        self._pending_outcome_time: float = 0
        # Continuous recording task
        self._continuous_task: asyncio.Task | None = None
        # First frame of sequence for before/after comparison
        self._sequence_first_frame: bytes | None = None
        # Outcome prompting
        self._needs_outcome_prompt: bool = False

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

    async def update_environment(self, env_type: str, setting: str, space: str):
        """Update environment classification on the session row."""
        if not self._session_id:
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/spatial_sessions?id=eq.{self._session_id}",
                    headers=_SERVICE_HEADERS,
                    json={
                        "environment_type": env_type or None,
                        "environment_setting": setting or None,
                        "environment_space": space or None,
                    },
                    timeout=5,
                )
            logger.info(f"Session environment updated: {env_type}/{setting}/{space}")
        except Exception as e:
            logger.error(f"Error updating session environment: {e}")

    async def update_task_type(self, task_type: str):
        """Update task type on the session row."""
        if not self._session_id or not task_type:
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/spatial_sessions?id=eq.{self._session_id}",
                    headers=_SERVICE_HEADERS,
                    json={"task_type": task_type},
                    timeout=5,
                )
            logger.info(f"Session task_type updated: {task_type}")
        except Exception as e:
            logger.error(f"Error updating session task_type: {e}")

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

    async def start_sequence(self, task_description: str = "", equipment: dict | None = None, task_type: str = ""):
        """Start a new clip sequence (job/workflow). Called when guidance starts or new task inferred."""
        if not self._session_id or not self._consent:
            return
        equip = equipment or {}
        seq_id = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SUPABASE_URL}/rest/v1/spatial_sequences",
                    headers=_SERVICE_HEADERS,
                    json={
                        "id": seq_id,
                        "session_id": self._session_id,
                        "user_id": self._user_id,
                        "task_description": task_description,
                        "task_type": task_type or None,
                        "equipment_type": equip.get("type"),
                        "equipment_brand": equip.get("brand"),
                        "equipment_model": equip.get("model"),
                    },
                    timeout=10,
                )
                if resp.status_code in (200, 201):
                    self._current_sequence_id = seq_id
                    self._sequence_order = 0
                    self._last_clip_id = None
                    logger.info(f"Spatial sequence started: {seq_id} ({task_description[:60]})")
        except Exception as e:
            logger.error(f"Error creating spatial sequence: {e}")

    async def end_sequence(self, outcome: str = "unknown"):
        """End current sequence. Adds state labels if first/last frames differ."""
        if not self._current_sequence_id:
            return

        # Mark last clip as sequence boundary for before/after training
        if self._sequence_first_frame and self._last_clip_id:
            await self.add_labels(self._last_clip_id, [
                {"label_type": "state", "label_value": "sequence_end", "confidence": 0.8},
            ])

        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/spatial_sequences?id=eq.{self._current_sequence_id}",
                    headers=_SERVICE_HEADERS,
                    json={
                        "ended_at": datetime.utcnow().isoformat(),
                        "clip_count": self._sequence_order,
                        "outcome": outcome,
                    },
                    timeout=10,
                )
            logger.info(f"Spatial sequence ended: {self._current_sequence_id} ({self._sequence_order} clips, outcome={outcome})")
        except Exception as e:
            logger.error(f"Error ending spatial sequence: {e}")

        # Set up outcome inference — if no follow-up for 10 mins, assume fixed
        if outcome == "unknown":
            self._pending_outcome_sequence_id = self._current_sequence_id
            self._pending_outcome_time = time.time()
            self._pending_outcome_clip_id = self._last_clip_id  # Save before clearing

        self._current_sequence_id = None
        self._sequence_order = 0
        self._last_clip_id = None
        self._sequence_first_frame = None

    async def check_outcome_inference(self):
        """Check if we should infer outcome for a pending sequence.
        Called periodically — if no queries for 10+ minutes after sequence ended, assume fixed."""
        if not self._pending_outcome_sequence_id:
            return
        if time.time() - self._pending_outcome_time < _OUTCOME_INFER_SECONDS:
            return
        # No follow-up for 10 minutes → infer success
        await self._update_sequence_outcome(self._pending_outcome_sequence_id, "inferred_fixed")
        clip_id = getattr(self, '_pending_outcome_clip_id', None)
        if clip_id:
            await self.add_labels(clip_id, [
                {"label_type": "outcome", "label_value": "inferred_fixed", "confidence": 0.6}
            ])
        logger.info(f"Outcome inferred as fixed for sequence {self._pending_outcome_sequence_id}")
        self._pending_outcome_sequence_id = None

    async def set_outcome(self, outcome: str):
        """Explicitly set outcome for current or pending sequence. Called when user confirms."""
        seq_id = self._current_sequence_id or self._pending_outcome_sequence_id
        if not seq_id:
            return
        await self._update_sequence_outcome(seq_id, outcome)
        if self._last_clip_id:
            await self.add_labels(self._last_clip_id, [
                {"label_type": "outcome", "label_value": outcome, "confidence": 1.0}
            ])
        self._pending_outcome_sequence_id = None
        logger.info(f"Outcome set: {outcome} for sequence {seq_id}")

    async def _check_informal_sequence(self, agent) -> bool:
        """Detect if we should auto-create a sequence from repeated equipment queries.
        Also auto-closes stale informal sequences when equipment changes or timeout.
        Returns True if a new informal sequence was started."""

        # Build equipment key from current agent state
        equip_type = getattr(agent, '_equipment_type', '') or ''
        equip_brand = getattr(agent, '_equipment_brand', '') or ''
        equip_key = f"{equip_type}:{equip_brand}".lower().strip(":")

        now = time.time()

        # Auto-close stale informal sequences
        if self._current_sequence_id and self._last_query_time > 0:
            time_since_last = now - self._last_query_time
            equipment_changed = equip_key and equip_key != self._last_equipment_key
            timed_out = time_since_last > _INFORMAL_SEQUENCE_WINDOW

            if equipment_changed or timed_out:
                # Close the old informal sequence — compare frames for state label
                await self._compare_sequence_frames(agent)
                await self.end_sequence(outcome="unknown")
                self._needs_outcome_prompt = True
                logger.info(f"Informal sequence auto-closed (changed={equipment_changed}, timeout={timed_out})")

        if self._current_sequence_id:
            return False  # Already in a sequence (guided or still open)

        if not equip_key:
            return False

        # Same equipment within window → auto-create sequence
        if equip_key == self._last_equipment_key and (now - self._last_query_time) < _INFORMAL_SEQUENCE_WINDOW:
            agent_task_type = getattr(agent, '_task_type', '')
            await self.start_sequence(
                task_description=f"informal: repeated queries about {equip_type} {equip_brand}".strip(),
                equipment={"type": equip_type, "brand": equip_brand},
                task_type=agent_task_type,
            )
            logger.info(f"Informal sequence started: {equip_key}")
            return True

        self._last_equipment_key = equip_key
        self._last_query_time = now
        return False

    async def _compare_sequence_frames(self, agent):
        """Compare first frame of sequence to current frame using perceptual hash.
        Adds state_change label if frames differ significantly."""
        if not self._sequence_first_frame or not self._last_clip_id:
            return

        try:
            current_b64 = getattr(agent, '_latest_frame', None)
            if not current_b64:
                return
            current_frame = base64.b64decode(current_b64)

            # Simple perceptual comparison: resize both to 8x8 grayscale, compare
            from PIL import Image
            import io
            import hashlib

            def _phash(jpeg_bytes: bytes) -> int:
                """Simple perceptual hash: resize to 8x8 grayscale, compare to mean."""
                img = Image.open(io.BytesIO(jpeg_bytes)).convert('L').resize((8, 8))
                pixels = list(img.getdata())
                mean = sum(pixels) / len(pixels)
                return sum(1 << i for i, p in enumerate(pixels) if p > mean)

            hash_first = _phash(self._sequence_first_frame)
            hash_last = _phash(current_frame)

            # Hamming distance: count differing bits
            diff = bin(hash_first ^ hash_last).count('1')
            # 64 total bits, threshold of 10 = ~15% difference = meaningful change
            state_changed = diff > 10
            confidence = min(diff / 32.0, 1.0)  # Scale diff to 0-1 confidence

            await self.add_labels(self._last_clip_id, [
                {"label_type": "state", "label_value": "changed" if state_changed else "unchanged", "confidence": confidence},
            ])
            logger.info(f"Frame comparison: hamming={diff}/64, changed={state_changed}")

        except Exception as e:
            logger.debug(f"Frame comparison failed: {e}")

    def should_prompt_outcome(self) -> bool:
        """Check if we should ask the user 'did that fix it?'
        Returns True once after a sequence ends, then resets."""
        if getattr(self, '_needs_outcome_prompt', False):
            self._needs_outcome_prompt = False
            return True
        return False

    async def start_continuous_recording(self, agent, interval: int = 60):
        """Start continuous background recording at intervals. For Voice Mode data collection."""
        if self._continuous_task and not self._continuous_task.done():
            return  # Already running

        async def _continuous_loop():
            while True:
                await asyncio.sleep(interval)
                if not self._consent or not self._session_id:
                    continue
                if self._recording:
                    continue  # Don't overlap with triggered recordings
                frame = getattr(agent, "_latest_frame", None)
                if not frame:
                    continue
                # Record a short clip
                self._recording = True
                await self._record_clip(
                    trigger_type="continuous",
                    trigger_text="",
                    agent=agent,
                    monitor_state="continuous",
                    duration=15,
                )

        self._continuous_task = asyncio.create_task(_continuous_loop())
        logger.info("Continuous recording started")

    async def stop_continuous_recording(self):
        """Stop continuous background recording."""
        if self._continuous_task and not self._continuous_task.done():
            self._continuous_task.cancel()
            self._continuous_task = None
            logger.info("Continuous recording stopped")

    async def add_labels(self, clip_id: str, labels: list[dict]):
        """Add labels to a clip. Each label: {label_type, label_value, confidence}"""
        if not labels:
            return
        rows = []
        for label in labels:
            rows.append({
                "clip_id": clip_id,
                "label_type": label.get("label_type", ""),
                "label_value": label.get("label_value", ""),
                "confidence": label.get("confidence", 1.0),
            })
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/spatial_labels",
                    headers=_SERVICE_HEADERS,
                    json=rows,
                    timeout=10,
                )
        except Exception as e:
            logger.error(f"Error adding labels: {e}")

    def _extract_labels(self, trigger_type: str, trigger_text: str, agent) -> list[dict]:
        """Auto-extract labels from trigger context."""
        labels = []
        # Semantic label — what did the user ask
        if trigger_text:
            labels.append({"label_type": "semantic", "label_value": trigger_text[:500], "confidence": 1.0})

        # Equipment labels
        if hasattr(agent, '_equipment_type') and agent._equipment_type:
            labels.append({"label_type": "equipment", "label_value": agent._equipment_type, "confidence": 0.9})
        if hasattr(agent, '_equipment_brand') and agent._equipment_brand:
            labels.append({"label_type": "equipment", "label_value": f"brand:{agent._equipment_brand}", "confidence": 0.9})

        # Workflow stage from scene memory
        if hasattr(agent, '_scene') and agent._scene.stage:
            labels.append({"label_type": "workflow", "label_value": agent._scene.stage, "confidence": 0.7})

        # Activity from scene memory — with freshness check
        if hasattr(agent, '_scene') and agent._scene.activity:
            scene_age = time.time() - getattr(agent._scene, 'last_updated', 0)
            activity_confidence = 0.6 if scene_age < _ACTIVITY_STALE_SECONDS else 0.2
            labels.append({"label_type": "action", "label_value": agent._scene.activity, "confidence": activity_confidence})
            if activity_confidence < 0.5:
                labels.append({"label_type": "meta", "label_value": "stale_activity", "confidence": 1.0})

        # Object labels from scene memory
        if hasattr(agent, '_scene') and agent._scene.objects:
            for obj in agent._scene.objects[:5]:
                labels.append({"label_type": "object", "label_value": obj, "confidence": 0.6})

        # Guidance context
        if hasattr(agent, '_guidance_active') and agent._guidance_active:
            labels.append({"label_type": "workflow", "label_value": "guided", "confidence": 1.0})
            if hasattr(agent, '_guidance_task') and agent._guidance_task:
                labels.append({"label_type": "semantic", "label_value": f"task:{agent._guidance_task}", "confidence": 1.0})

        # Task type — session-level classification (diagnostic/install/repair/inspect/maintenance)
        if hasattr(agent, '_task_type') and agent._task_type:
            labels.append({"label_type": "task_type", "label_value": agent._task_type, "confidence": 0.85})

        # Environment — session-level classification
        if hasattr(agent, '_environment_type') and agent._environment_type:
            labels.append({"label_type": "environment", "label_value": agent._environment_type, "confidence": 0.9})
        if hasattr(agent, '_environment_setting') and agent._environment_setting:
            labels.append({"label_type": "environment", "label_value": agent._environment_setting, "confidence": 0.9})
        if hasattr(agent, '_environment_space') and agent._environment_space:
            labels.append({"label_type": "environment", "label_value": f"space:{agent._environment_space}", "confidence": 0.85})

        # Action taken — structured extraction from trigger text
        if trigger_text:
            action = _extract_action_label(trigger_text)
            if action:
                labels.append({"label_type": "action_taken", "label_value": action, "confidence": 0.8})

        return labels


def _extract_action_label(text: str) -> str:
    """Extract a structured action label from the user's transcript.
    Maps natural speech to a normalized action verb."""
    t = text.lower()
    action_map = [
        (["replac", "swap", "change out", "changing out"], "replacing"),
        (["install", "putting in", "hook up", "hooking up", "adding"], "installing"),
        (["repair", "fix", "patch", "sealing"], "repairing"),
        (["troubleshoot", "diagnos", "why is", "figure out"], "diagnosing"),
        (["check", "inspect", "test", "look at", "verify"], "inspecting"),
        (["wire", "wiring", "connect", "terminate"], "wiring"),
        (["flush", "drain", "bleed"], "draining"),
        (["clean", "service", "maintain"], "maintaining"),
        (["cut", "cut in", "rough in"], "roughing_in"),
        (["charge", "recharge", "add refrigerant"], "charging"),
    ]
    for keywords, action in action_map:
        if any(kw in t for kw in keywords):
            return action
    return ""

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

        # Check informal sequence (same equipment, within time window)
        if trigger_type == 'user_query':
            await self._check_informal_sequence(agent)
            self._last_query_time = time.time()

        # Save first frame of sequence for before/after comparison
        if self._current_sequence_id and self._sequence_order == 0:
            try:
                self._sequence_first_frame = base64.b64decode(agent._latest_frame)
            except Exception:
                pass

        # Set recording flag BEFORE launching task to prevent concurrent clips
        self._recording = True
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
        # _recording flag already set by trigger_recording before ensure_future

        try:
            # Track sequence
            self._sequence_order += 1

            # Determine workflow stage from scene memory
            workflow_stage = None
            if hasattr(agent, '_scene') and agent._scene.stage:
                workflow_stage = agent._scene.stage

            # 1. Create clip record in Supabase with sequence data
            clip_row = {
                "id": clip_id,
                "session_id": self._session_id,
                "s3_key": s3_key,
                "trigger_type": trigger_type,
                "trigger_text": (trigger_text or "")[:2000],
                "monitor_state": monitor_state,
                "status": "recording",
                "resolution": "720x1280",
                "sequence_id": self._current_sequence_id,
                "sequence_order": self._sequence_order,
                "parent_clip_id": self._last_clip_id,
                "workflow_stage": workflow_stage,
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
            self._last_clip_id = clip_id
            logger.info(f"Clip {clip_id} ready: s3://{s3_key} ({len(mp4_data)} bytes, {len(frames)} frames)")

            # 6. Auto-generate labels from context
            try:
                labels = self._extract_labels(trigger_type, trigger_text, agent)
                if labels:
                    await self.add_labels(clip_id, labels)
                    logger.info(f"Clip {clip_id}: {len(labels)} labels added")
            except Exception as e:
                logger.debug(f"Label generation failed for {clip_id}: {e}")

        except Exception as e:
            logger.error(f"Clip {clip_id} failed: {e}")
            try:
                await self._update_clip_status(clip_id, "failed", error=str(e)[:500])
            except Exception:
                pass
        finally:
            self._recording = False

    async def _encode_mp4(self, frames: list[bytes], fps: int = 2) -> bytes | None:
        """Encode JPEG frames to MP4 via ffmpeg (uses imageio-ffmpeg bundled binary)."""
        try:
            # Get ffmpeg binary path from imageio-ffmpeg (pip-installed, no system ffmpeg needed)
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            proc = await asyncio.create_subprocess_exec(
                ffmpeg_path,
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

            input_data = b"".join(frames)
            stdout, stderr = await proc.communicate(input=input_data)

            if proc.returncode != 0:
                logger.error(f"ffmpeg failed (rc={proc.returncode}): {stderr.decode()[:500]}")
                return None

            return stdout

        except ImportError:
            logger.error("imageio-ffmpeg not installed — pip install imageio-ffmpeg")
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

    async def _update_sequence_outcome(self, sequence_id: str, outcome: str):
        """Update outcome on a sequence."""
        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/spatial_sequences?id=eq.{sequence_id}",
                    headers=_SERVICE_HEADERS,
                    json={"outcome": outcome},
                    timeout=10,
                )
        except Exception as e:
            logger.error(f"Failed to update sequence outcome: {e}")

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
