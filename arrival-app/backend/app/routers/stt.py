"""
Speech-to-Text router — POST /api/stt
Accepts base64-encoded audio, returns transcribed text.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.demo import get_demo_transcription
from app.services.deepgram import transcribe_audio
from app.middleware.auth import get_current_user

router = APIRouter()

MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB raw; base64 is ~1.37x larger


class STTRequest(BaseModel):
    audio_base64: str


class STTResponse(BaseModel):
    text: str


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    request: STTRequest,
    req: Request,
    demo: bool = Query(False, description="Use demo mode (no API key needed)"),
):
    """
    Convert speech audio to text.
    Pass ?demo=true for canned responses without API keys.
    """
    # Validate audio size before processing
    if len(request.audio_base64) > MAX_AUDIO_SIZE * 1.37:
        raise HTTPException(status_code=400, detail="Audio too large (max 10 MB)")

    try:
        if demo:
            text = get_demo_transcription()
        else:
            # Auth required for non-demo requests
            user = await get_current_user(req)
            text = await transcribe_audio(request.audio_base64)

        return STTResponse(text=text)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
