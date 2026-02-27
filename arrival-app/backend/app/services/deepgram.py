"""
Speech-to-Text service using Deepgram Nova-2 API.
"""

import base64
import httpx

from app.config import DEEPGRAM_API_KEY

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


def _detect_audio_content_type(audio_bytes: bytes) -> str:
    """Detect audio content type from magic bytes. Defaults to audio/mp4."""
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
    if len(audio_bytes) >= 8 and audio_bytes[4:8] == b"ftyp":
        return "audio/mp4"
    return "audio/mp4"  # default fallback


async def transcribe_audio(audio_base64: str) -> str:
    """
    Send base64-encoded audio to Deepgram and return transcribed text.
    Supports WAV, MP3, M4A, WebM formats.
    """
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY not set. Add it to your .env file.")

    audio_bytes = base64.b64decode(audio_base64)
    content_type = _detect_audio_content_type(audio_bytes)

    async with httpx.AsyncClient(timeout=30.0) as client:
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
