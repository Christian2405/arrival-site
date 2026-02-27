"""
Text-to-Speech service using ElevenLabs API.
Uses a shared httpx client for connection pooling.
"""

import base64
import logging
import time

import httpx

from app import config

logger = logging.getLogger(__name__)

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Shared client — reuses TCP+TLS connections across requests
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def text_to_speech(
    text: str,
    voice_id: str | None = None,
    voice_settings: dict | None = None,
) -> str:
    """
    Convert text to speech using ElevenLabs.
    Returns base64-encoded MP3 audio.
    """
    if not config.ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not set. Add it to your .env file.")

    t0 = time.monotonic()
    url = f"{ELEVENLABS_URL}/{voice_id or config.ELEVENLABS_VOICE_ID}"

    default_voice_settings = {
        "stability": 0.4,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
        "speed": 1.15,
    }

    client = _get_client()
    response = await client.post(
        url,
        headers={
            "xi-api-key": config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": text,
            "model_id": "eleven_flash_v2_5",
            "voice_settings": voice_settings if voice_settings is not None else default_voice_settings,
        },
    )

    elapsed = time.monotonic() - t0

    if response.status_code != 200:
        detail = response.text[:200]
        logger.error(f"[tts] ElevenLabs {response.status_code} in {elapsed:.2f}s: {detail}")
        raise ValueError(f"TTS failed ({response.status_code}): {detail}")

    audio_b64 = base64.b64encode(response.content).decode("utf-8")
    audio_size_kb = len(response.content) / 1024
    logger.info(f"[tts] {len(text)} chars → {audio_size_kb:.0f}KB audio in {elapsed:.2f}s")
    return audio_b64
