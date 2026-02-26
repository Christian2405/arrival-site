"""
Text-to-Speech service using ElevenLabs API.
"""

import base64
import logging
import os

import httpx

from app import config

logger = logging.getLogger(__name__)

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


async def text_to_speech(text: str) -> str:
    """
    Convert text to speech using ElevenLabs.
    Returns base64-encoded MP3 audio.
    """
    # Read the key directly from the environment as a fallback
    api_key = config.ELEVENLABS_API_KEY or os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = config.ELEVENLABS_VOICE_ID

    logger.info(
        f"[tts] key len={len(api_key)}, "
        f"first5={api_key[:5] if api_key else 'EMPTY'}, "
        f"voice={voice_id}"
    )

    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not set. Add it to your .env file.")

    url = f"{ELEVENLABS_URL}/{voice_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.4,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True,
                    "speed": 1.15,
                },
            },
        )

        if response.status_code != 200:
            logger.error(
                f"[tts] ElevenLabs returned {response.status_code}: "
                f"{response.text[:200]}"
            )

        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
