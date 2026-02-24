"""
Speech-to-Text router — POST /api/stt
Accepts base64-encoded audio, returns transcribed text.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.demo import get_demo_transcription
from app.services.deepgram import transcribe_audio

router = APIRouter()


class STTRequest(BaseModel):
    audio_base64: str


class STTResponse(BaseModel):
    text: str


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    request: STTRequest,
    demo: bool = Query(False, description="Use demo mode (no API key needed)"),
):
    """
    Convert speech audio to text.
    Pass ?demo=true for canned responses without API keys.
    """
    try:
        if demo:
            text = get_demo_transcription()
        else:
            text = await transcribe_audio(request.audio_base64)

        return STTResponse(text=text)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
