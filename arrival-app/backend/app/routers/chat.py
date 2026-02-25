"""
Chat router — POST /api/chat
Sends a message (optionally with camera image) to Claude, returns AI response.
Now includes: JWT auth, Mem0 memory retrieval/storage, RAG document context.
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.demo import get_demo_chat_response
from app.services.anthropic import chat_with_claude
from app.services.memory import retrieve_memories, store_memory
from app.services.rag import retrieve_context
from app.services.supabase import log_query, get_user_team_id
from app.middleware.auth import get_current_user

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
    req: Request,
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
            # 1. Get authenticated user
            user = await get_current_user(req)
            user_id = user["user_id"]

            # 2. Retrieve memories for this user
            memories = await retrieve_memories(user_id, request.message)

            # 3. Retrieve relevant document context (RAG)
            rag_context = await retrieve_context(user_id, request.message)

            # 4. Call Claude with memories + RAG context
            result = await chat_with_claude(
                message=request.message,
                image_base64=request.image_base64,
                conversation_history=request.conversation_history,
                user_memories=memories,
                rag_context=rag_context,
            )

            # 5. Store new memories (fire-and-forget, non-blocking)
            asyncio.create_task(store_memory(user_id, [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": result["response"]},
            ]))

            # 6. Log query for team activity (fire-and-forget, non-blocking)
            async def _log():
                team_id = await get_user_team_id(user_id)
                await log_query(
                    user_id=user_id,
                    question=request.message,
                    response=result.get("response"),
                    source=result.get("source"),
                    confidence=result.get("confidence"),
                    has_image=bool(request.image_base64),
                    team_id=team_id,
                )
            asyncio.create_task(_log())

        return ChatResponse(
            response=result["response"],
            source=result.get("source"),
            confidence=result.get("confidence"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
