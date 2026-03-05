"""
Deepgram Live WebSocket STT service.
Streams audio to Deepgram in real-time, returns interim and final transcripts.
Replaces the REST-based deepgram.py for the streaming voice pipeline.
Server-side endpointing replaces client-side VAD.
"""

import asyncio
import json
import logging
import time
from typing import Callable, Awaitable

import websockets
from websockets.asyncio.client import ClientConnection

from app.config import DEEPGRAM_API_KEY

logger = logging.getLogger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramLiveSession:
    """
    Manages a live WebSocket connection to Deepgram Nova-2.

    Usage:
        session = DeepgramLiveSession(
            on_interim_transcript=...,
            on_final_transcript=...,
            on_speech_final=...,
        )
        await session.connect()
        await session.send_audio(pcm_bytes)  # call repeatedly with 200ms chunks
        await session.close()
    """

    def __init__(
        self,
        on_interim_transcript: Callable[[str], Awaitable[None]] | None = None,
        on_final_transcript: Callable[[str], Awaitable[None]] | None = None,
        on_speech_final: Callable[[str], Awaitable[None]] | None = None,
        on_error: Callable[[str], Awaitable[None]] | None = None,
        endpointing_ms: int = 300,
        utterance_end_ms: int = 1200,
    ):
        self._on_interim = on_interim_transcript
        self._on_final = on_final_transcript
        self._on_speech_final = on_speech_final
        self._on_error = on_error
        self._endpointing_ms = endpointing_ms
        self._utterance_end_ms = utterance_end_ms

        self._ws: ClientConnection | None = None
        self._receive_task: asyncio.Task | None = None
        self._connected = False
        self._closing = False

        # Accumulate final transcript chunks until utterance_end
        self._utterance_transcript = ""
        self._last_final_time = 0.0

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Open a WebSocket connection to Deepgram Live API."""
        if not DEEPGRAM_API_KEY:
            raise ValueError("DEEPGRAM_API_KEY not set")

        params = (
            f"?model=nova-2"
            f"&language=en-US"
            f"&smart_format=true"
            f"&interim_results=true"
            f"&endpointing={self._endpointing_ms}"
            f"&utterance_end_ms={self._utterance_end_ms}"
            f"&encoding=linear16"
            f"&sample_rate=16000"
            f"&channels=1"
            f"&vad_events=true"
        )

        url = DEEPGRAM_WS_URL + params
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

        try:
            self._ws = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            self._closing = False
            self._utterance_transcript = ""
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info("[deepgram-live] Connected to Deepgram Live WebSocket")
        except Exception as e:
            logger.error(f"[deepgram-live] Connection failed: {e}")
            raise

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Send raw PCM audio bytes to Deepgram. Call with 200ms chunks."""
        if self._ws and self._connected and not self._closing:
            try:
                await self._ws.send(pcm_bytes)
            except Exception as e:
                logger.warning(f"[deepgram-live] Send failed: {e}")

    async def close(self) -> None:
        """Gracefully close the Deepgram WebSocket connection."""
        self._closing = True
        if self._ws and self._connected:
            try:
                # Send close message to Deepgram
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await asyncio.sleep(0.2)  # Brief wait for final results
            except Exception:
                pass
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
        logger.info("[deepgram-live] Connection closed")

    async def _receive_loop(self) -> None:
        """Background task that receives messages from Deepgram."""
        try:
            async for raw_msg in self._ws:
                if self._closing:
                    break
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_message(msg)
                except json.JSONDecodeError:
                    logger.warning(f"[deepgram-live] Non-JSON message: {str(raw_msg)[:100]}")
                except Exception as e:
                    logger.error(f"[deepgram-live] Message handler error: {e}", exc_info=True)
        except websockets.exceptions.ConnectionClosed as e:
            if not self._closing:
                logger.warning(f"[deepgram-live] Connection closed unexpectedly: {e}")
                if self._on_error:
                    await self._on_error(f"Deepgram connection lost: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[deepgram-live] Receive loop error: {e}", exc_info=True)
            if self._on_error:
                await self._on_error(str(e))
        finally:
            self._connected = False

    async def _handle_message(self, msg: dict) -> None:
        """Process a message from Deepgram."""
        msg_type = msg.get("type", "")

        if msg_type == "Results":
            channel = msg.get("channel", {})
            alternatives = channel.get("alternatives", [])
            if not alternatives:
                return

            transcript = alternatives[0].get("transcript", "").strip()
            is_final = msg.get("is_final", False)
            speech_final = msg.get("speech_final", False)

            if not transcript:
                # Empty transcript on speech_final means end of utterance
                if speech_final and self._utterance_transcript:
                    full = self._utterance_transcript.strip()
                    self._utterance_transcript = ""
                    logger.info(f"[deepgram-live] Speech final (empty): '{full[:60]}'")
                    if self._on_speech_final:
                        await self._on_speech_final(full)
                return

            if is_final:
                # Accumulate final transcript chunks
                self._utterance_transcript += " " + transcript
                self._last_final_time = time.monotonic()

                if self._on_final:
                    await self._on_final(transcript)

                # If speech_final is also true, this utterance is complete
                if speech_final:
                    full = self._utterance_transcript.strip()
                    self._utterance_transcript = ""
                    logger.info(f"[deepgram-live] Speech final: '{full[:60]}'")
                    if self._on_speech_final:
                        await self._on_speech_final(full)
            else:
                # Interim result — show in UI but don't accumulate
                if self._on_interim:
                    # Include any accumulated finals + this interim
                    display = (self._utterance_transcript + " " + transcript).strip()
                    await self._on_interim(display)

        elif msg_type == "UtteranceEnd":
            # Deepgram's utterance_end_ms timeout fired
            if self._utterance_transcript:
                full = self._utterance_transcript.strip()
                self._utterance_transcript = ""
                logger.info(f"[deepgram-live] Utterance end: '{full[:60]}'")
                if self._on_speech_final:
                    await self._on_speech_final(full)

        elif msg_type == "SpeechStarted":
            logger.debug("[deepgram-live] Speech started")

        elif msg_type == "Metadata":
            logger.debug(f"[deepgram-live] Metadata: request_id={msg.get('request_id', 'N/A')}")

        elif msg_type == "Error":
            error_msg = msg.get("message", "Unknown Deepgram error")
            logger.error(f"[deepgram-live] Error: {error_msg}")
            if self._on_error:
                await self._on_error(error_msg)

    def reset_utterance(self) -> None:
        """Reset the utterance accumulator (e.g., after interrupt)."""
        self._utterance_transcript = ""
