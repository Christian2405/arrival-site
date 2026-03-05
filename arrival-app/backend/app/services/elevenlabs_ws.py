"""
ElevenLabs WebSocket Streaming TTS service.
Streams text chunks to ElevenLabs and receives MP3 audio chunks in real-time.
Replaces the REST-based elevenlabs.py for the streaming voice pipeline.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Callable, Awaitable

import websockets
from websockets.asyncio.client import ClientConnection

from app import config

logger = logging.getLogger(__name__)

ELEVENLABS_WS_URL = "wss://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsStreamSession:
    """
    Manages a streaming WebSocket connection to ElevenLabs TTS.

    Usage:
        session = ElevenLabsStreamSession(
            on_audio_chunk=callback,  # receives raw MP3 bytes
            voice_id="...",
        )
        await session.connect()
        await session.send_text("First sentence. ")  # note trailing space
        await session.send_text("Second sentence. ")
        await session.flush()  # signal end of text, get remaining audio
        await session.close()
    """

    def __init__(
        self,
        on_audio_chunk: Callable[[bytes], Awaitable[None]],
        on_done: Callable[[], Awaitable[None]] | None = None,
        on_error: Callable[[str], Awaitable[None]] | None = None,
        voice_id: str | None = None,
        voice_settings: dict | None = None,
    ):
        self._on_audio_chunk = on_audio_chunk
        self._on_done = on_done
        self._on_error = on_error
        self._voice_id = voice_id or config.ELEVENLABS_VOICE_ID
        self._voice_settings = voice_settings or {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True,
        }

        self._ws: ClientConnection | None = None
        self._receive_task: asyncio.Task | None = None
        self._connected = False
        self._closing = False
        self._total_audio_bytes = 0
        self._t0 = 0.0

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Open a WebSocket connection to ElevenLabs streaming TTS."""
        if not config.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY not set")

        url = (
            f"{ELEVENLABS_WS_URL}/{self._voice_id}/stream-input"
            f"?model_id=eleven_flash_v2_5"
            f"&output_format=mp3_44100_128"
        )

        try:
            self._ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            self._closing = False
            self._total_audio_bytes = 0
            self._t0 = time.monotonic()

            # Send BOS (Begin of Stream) with config
            bos = {
                "text": " ",
                "voice_settings": self._voice_settings,
                "xi_api_key": config.ELEVENLABS_API_KEY,
                "generation_config": {
                    "chunk_length_schedule": [120, 160, 250, 290],
                },
            }
            await self._ws.send(json.dumps(bos))

            # Start receiving audio chunks
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info(f"[elevenlabs-ws] Connected (voice={self._voice_id})")
        except Exception as e:
            logger.error(f"[elevenlabs-ws] Connection failed: {e}")
            raise

    async def send_text(self, text: str) -> None:
        """Send a text chunk to be synthesized. Include trailing space for natural flow."""
        if self._ws and self._connected and not self._closing:
            try:
                await self._ws.send(json.dumps({
                    "text": text,
                    "try_trigger_generation": True,
                }))
            except Exception as e:
                logger.warning(f"[elevenlabs-ws] Send text failed: {e}")

    async def flush(self) -> None:
        """Signal end of text input. ElevenLabs will generate remaining audio."""
        if self._ws and self._connected and not self._closing:
            try:
                # Send EOS (End of Stream) — empty text signals flush
                await self._ws.send(json.dumps({"text": ""}))
            except Exception as e:
                logger.warning(f"[elevenlabs-ws] Flush failed: {e}")

    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._closing = True
        if self._ws and self._connected:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._connected = False
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        elapsed = time.monotonic() - self._t0 if self._t0 else 0
        logger.info(
            f"[elevenlabs-ws] Closed — {self._total_audio_bytes / 1024:.0f}KB audio in {elapsed:.2f}s"
        )

    async def _receive_loop(self) -> None:
        """Background task that receives audio chunks from ElevenLabs."""
        first_chunk = True
        try:
            async for raw_msg in self._ws:
                if self._closing:
                    break
                try:
                    msg = json.loads(raw_msg)
                    audio_b64 = msg.get("audio")
                    is_final = msg.get("isFinal", False)

                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        self._total_audio_bytes += len(audio_bytes)

                        if first_chunk:
                            elapsed = time.monotonic() - self._t0
                            logger.info(f"[elevenlabs-ws] First audio chunk in {elapsed:.2f}s ({len(audio_bytes)} bytes)")
                            first_chunk = False

                        await self._on_audio_chunk(audio_bytes)

                    if is_final:
                        logger.debug("[elevenlabs-ws] Received final chunk")
                        if self._on_done:
                            await self._on_done()
                        break

                except json.JSONDecodeError:
                    # Binary frame? Shouldn't happen with ElevenLabs WS
                    logger.warning(f"[elevenlabs-ws] Non-JSON message received")
                except Exception as e:
                    logger.error(f"[elevenlabs-ws] Message handler error: {e}", exc_info=True)

        except websockets.exceptions.ConnectionClosed as e:
            if not self._closing:
                logger.warning(f"[elevenlabs-ws] Connection closed: {e}")
                if self._on_error:
                    await self._on_error(f"ElevenLabs connection lost: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[elevenlabs-ws] Receive loop error: {e}", exc_info=True)
            if self._on_error:
                await self._on_error(str(e))
        finally:
            self._connected = False
