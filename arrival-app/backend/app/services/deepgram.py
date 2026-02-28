"""
Speech-to-Text service using Deepgram Nova-2 API.
Uses a shared httpx client for connection pooling (avoids ~200ms TLS overhead per request).
"""

import base64
import httpx
import logging
import time

from app.config import DEEPGRAM_API_KEY

logger = logging.getLogger(__name__)

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# Shared client — reuses TCP+TLS connections across requests
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


def _detect_audio_content_type(audio_bytes: bytes) -> str:
    """Detect audio content type from magic bytes. Defaults to audio/mp4."""
    if len(audio_bytes) < 12:
        logger.warning(f"[stt] Audio too short for format detection ({len(audio_bytes)} bytes)")
        return "audio/mp4"
    if audio_bytes[:4] == b"\x1aE\xdf\xa3":
        return "audio/webm"
    if audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb" or audio_bytes[:2] == b"\xff\xf3":
        return "audio/mpeg"
    if audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        return "audio/wav"
    if audio_bytes[:4] == b"fLaC":
        return "audio/flac"
    if audio_bytes[:4] == b"OggS":
        return "audio/ogg"
    # m4a/mp4 — check for 'ftyp' box at offset 4
    if audio_bytes[4:8] == b"ftyp":
        return "audio/mp4"
    logger.info(f"[stt] Unknown audio format (magic: {audio_bytes[:8].hex()}), defaulting to audio/mp4")
    return "audio/mp4"  # default fallback


async def transcribe_audio(audio_base64: str) -> str:
    """
    Send base64-encoded audio to Deepgram and return transcribed text.
    Supports WAV, MP3, M4A, WebM formats.
    """
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY not set. Add it to your .env file.")

    t0 = time.monotonic()
    audio_bytes = base64.b64decode(audio_base64)
    content_type = _detect_audio_content_type(audio_bytes)
    audio_size_kb = len(audio_bytes) / 1024

    client = _get_client()
    response = await client.post(
        DEEPGRAM_URL,
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": content_type,
        },
        params={
            "model": "nova-2",
            "smart_format": "true",
            "language": "en-US",
            "detect_language": "false",
        },
        content=audio_bytes,
    )

    elapsed = time.monotonic() - t0

    if response.status_code != 200:
        error_detail = response.text[:200]
        logger.error(f"[stt] Deepgram {response.status_code} in {elapsed:.2f}s: {error_detail}")
        raise Exception(f"Deepgram API error {response.status_code}: {error_detail}")

    result = response.json()

    channels = result.get("results", {}).get("channels", [])
    transcript = ""
    if channels:
        alternatives = channels[0].get("alternatives", [])
        if alternatives:
            transcript = alternatives[0].get("transcript", "")

    logger.info(f"[stt] {audio_size_kb:.0f}KB {content_type} → '{transcript[:50]}' in {elapsed:.2f}s")
    return transcript
