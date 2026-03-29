"""
TTS router — POST /api/tts
Converts text to speech audio using ElevenLabs.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.demo import generate_silent_audio_base64
from app.services.elevenlabs import text_to_speech
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Onboarding narration ---
_ONBOARDING_SCRIPT = (
    "Welcome to Arrival. Real-time AI guidance for trade workers.\n\n"
    "In Voice Mode, tap the button and ask anything. Wire sizes, torque specs, "
    "error codes, code requirements — you get a real answer in seconds.\n\n"
    "Switch to Job Mode when you're on site. Arrival watches through your camera "
    "while you work. It flags issues before they become problems. Need to walk "
    "through a job? Just say Guide Me — it walks you through it, hands free.\n\n"
    "You can also type questions or attach a photo in Text Mode.\n\n"
    "Upload your company manuals, SOPs, and spec sheets under Documents. "
    "Arrival pulls from them in every answer — your team's knowledge, always on site.\n\n"
    "Tap the mic to get started."
)

# Cache the generated audio in memory — only generate once per server restart
_narration_cache: str | None = None

MAX_TTS_TEXT = 5000  # max characters for TTS input


class TTSRequest(BaseModel):
    text: str


class TTSResponse(BaseModel):
    audio_base64: str


@router.get("/onboarding-narration")
async def get_onboarding_narration(req: Request):
    """
    Return the onboarding narration audio via ElevenLabs.
    Cached in memory after first generation — only one ElevenLabs call per server restart.
    """
    global _narration_cache

    # Auth required
    await get_current_user(req)

    if _narration_cache is None:
        logger.info("[onboarding] Generating narration audio...")
        _narration_cache = await text_to_speech(_ONBOARDING_SCRIPT)
        logger.info(f"[onboarding] Generated and cached — {len(_narration_cache)} chars b64")

    return {"audio_base64": _narration_cache}


@router.post("/tts", response_model=TTSResponse)
async def tts(
    request: TTSRequest,
    req: Request,
    demo: bool = Query(False, description="Use demo mode (no API key needed)"),
):
    """
    Text-to-Speech — convert text to audio.
    Pass ?demo=true for silent audio clip without API keys.
    """
    # Validate text length
    if len(request.text) > MAX_TTS_TEXT:
        raise HTTPException(status_code=400, detail=f"Text too long (max {MAX_TTS_TEXT} chars)")

    try:
        if demo:
            audio = generate_silent_audio_base64(duration_seconds=0.5)
        else:
            # Auth required for non-demo requests
            user = await get_current_user(req)
            audio = await text_to_speech(request.text)

        return TTSResponse(audio_base64=audio)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[tts] TTS failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TTS failed")
