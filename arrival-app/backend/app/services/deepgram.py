"""
Speech-to-Text service using Deepgram Nova-2 API.
"""

import base64
import httpx

from app.config import DEEPGRAM_API_KEY

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio(audio_base64: str) -> str:
    """
    Send base64-encoded audio to Deepgram and return transcribed text.
    Supports WAV, MP3, M4A, WebM formats.
    """
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY not set. Add it to your .env file.")

    audio_bytes = base64.b64decode(audio_base64)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            DEEPGRAM_URL,
            headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/mp4",  # Expo iOS records as m4a (mp4 container)
            },
            params={
                "model": "nova-2",
                "smart_format": "true",
                "language": "en-US",
                "detect_language": "false",
            },
            content=audio_bytes,
        )

        if response.status_code != 200:
            error_detail = response.text[:200]
            raise Exception(f"Deepgram API error {response.status_code}: {error_detail}")

        result = response.json()

        channels = result.get("results", {}).get("channels", [])
        if channels:
            alternatives = channels[0].get("alternatives", [])
            if alternatives:
                transcript = alternatives[0].get("transcript", "")
                if transcript:
                    return transcript

        return ""
