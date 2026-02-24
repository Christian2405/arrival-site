"""
TTS router — POST /api/tts
Converts text to speech audio using ElevenLabs.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.demo import generate_silent_audio_base64
from app.services.elevenlabs import text_to_speech

router = APIRouter()


class TTSRequest(BaseModel):
    text: str


class TTSResponse(BaseModel):
    audio_base64: str


@router.post("/tts", response_model=TTSResponse)
async def tts(
    request: TTSRequest,
    demo: bool = Query(False, description="Use demo mode (no API key needed)"),
):
    """
    Text-to-Speech — convert text to audio.
    Pass ?demo=true for silent audio clip without API keys.
    """
    try:
        if demo:
            audio = generate_silent_audio_base64(duration_seconds=0.5)
        else:
            audio = await text_to_speech(request.text)

        return TTSResponse(audio_base64=audio)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")
