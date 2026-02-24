"""
Chat router — POST /api/chat
Sends a message (optionally with camera image) to Claude, returns AI response.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.demo import get_demo_chat_response
from app.services.anthropic import chat_with_claude

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    image_base64: str | None = None
    conversation_history: list[dict] = []


class ChatResponse(BaseModel):
    response: str
    source: str | None = None
    confidence: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    demo: bool = Query(False, description="Use demo mode (no API key needed)"),
):
    """
    AI Chat — send a question with an optional camera frame.
    Pass ?demo=true for canned trade responses without API keys.
    """
    try:
        if demo:
            result = get_demo_chat_response(request.message)
        else:
            result = await chat_with_claude(
                message=request.message,
                image_base64=request.image_base64,
                conversation_history=request.conversation_history,
            )

        return ChatResponse(
            response=result["response"],
            source=result.get("source"),
            confidence=result.get("confidence"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
