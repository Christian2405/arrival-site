"""
Text-to-Speech service using ElevenLabs API.
"""

import base64
import logging

import httpx

from app import config

logger = logging.getLogger(__name__)

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


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

    url = f"{ELEVENLABS_URL}/{voice_id or config.ELEVENLABS_VOICE_ID}"

    default_voice_settings = {
        "stability": 0.4,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
        "speed": 1.15,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers={
                "xi-api-key": config.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": voice_settings if voice_settings is not None else default_voice_settings,
            },
        )

        if response.status_code != 200:
            logger.error(
                f"[tts] ElevenLabs returned {response.status_code}: "
                f"{response.text[:200]}"
            )

        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
