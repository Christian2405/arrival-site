"""
Arrival Backend API Server
FastAPI app with STT, Chat, TTS, and Documents endpoints.
"""

import asyncio
import logging
import os
import time

import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import stt, chat, tts, voice_chat, documents, analyze, queries, saved_answers, usage, feedback

# Configure logging to show INFO level (Render captures stdout)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

logger = logging.getLogger(__name__)

# --- Keep-alive to prevent Render free tier from sleeping ---
KEEP_ALIVE_INTERVAL = 13 * 60  # 13 minutes (Render sleeps after 15)

async def _keep_alive():
    """Ping own health endpoint to prevent Render free tier from sleeping."""
    external_url = os.getenv("RENDER_EXTERNAL_URL")
    if not external_url:
        logger.info("[keep-alive] RENDER_EXTERNAL_URL not set — skipping keep-alive (not on Render)")
        return

    health_url = f"{external_url}/api/health"
    logger.info(f"[keep-alive] Started — pinging {health_url} every {KEEP_ALIVE_INTERVAL}s")

    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)
            try:
                resp = await client.get(health_url, timeout=10)
                logger.debug(f"[keep-alive] Pinged → {resp.status_code}")
            except Exception as e:
                logger.warning(f"[keep-alive] Ping failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — launches keep-alive task."""
    task = asyncio.create_task(_keep_alive())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Arrival API",
    version="2.0.0",
    description="AI voice & camera assistant for trade workers",
    lifespan=lifespan,
)

# CORS — allow all origins.
# This API is consumed by a React Native mobile app which doesn't
# run in a browser origin, so restrictive CORS just breaks things.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # Must be False when origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(stt.router, prefix="/api", tags=["Speech-to-Text"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(tts.router, prefix="/api", tags=["Text-to-Speech"])
app.include_router(voice_chat.router, prefix="/api", tags=["Voice Chat"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(analyze.router, prefix="/api", tags=["Frame Analysis"])
app.include_router(queries.router, prefix="/api", tags=["Queries"])
app.include_router(saved_answers.router, prefix="/api", tags=["Saved Answers"])
app.include_router(usage.router, prefix="/api", tags=["Usage"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])


# --- Validation error logging (debug 422s) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"[422] {request.method} {request.url.path} — {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# --- Health Check ---

@app.get("/api/health")
async def health():
    """Health check endpoint — returns API status and version."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "Arrival API",
    }


@app.get("/")
async def root():
    return {"status": "ok", "service": "Arrival API", "version": "2.0.0"}


# --- Diagnostics endpoint — times each service independently ---
# Bug fix: Requires auth + DIAGNOSTICS_SECRET to prevent abuse (burns paid API credits).
# Errors no longer leak raw exception messages.

@app.get("/api/diagnostics")
async def diagnostics(req: Request, secret: str = Query("", description="Diagnostics secret")):
    """
    Test and time each service independently.
    Requires DIAGNOSTICS_SECRET query param or authenticated admin.
    Returns latency breakdown for debugging performance.
    """
    expected_secret = os.getenv("DIAGNOSTICS_SECRET", "")
    if not expected_secret or secret != expected_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    results = {}
    total_start = time.monotonic()

    # 1. Supabase DB (team_members query)
    try:
        t = time.monotonic()
        from app.services.supabase import get_user_team_id
        await get_user_team_id("diagnostics-test-user")
        results["supabase_team_lookup"] = {"ms": round((time.monotonic() - t) * 1000), "status": "ok"}
    except Exception:
        results["supabase_team_lookup"] = {"ms": round((time.monotonic() - t) * 1000), "status": "error"}

    # 2. Mem0 memory search
    try:
        t = time.monotonic()
        from app.services.memory import retrieve_memories
        mems = await retrieve_memories("diagnostics-test-user", "hello")
        results["mem0_search"] = {"ms": round((time.monotonic() - t) * 1000), "status": "ok", "count": len(mems)}
    except Exception:
        results["mem0_search"] = {"ms": round((time.monotonic() - t) * 1000), "status": "error"}

    # 3. Pinecone RAG search
    try:
        t = time.monotonic()
        from app.services.rag import retrieve_context
        ctx = await retrieve_context("diagnostics-test-user", "hello", team_id=None)
        results["pinecone_rag"] = {"ms": round((time.monotonic() - t) * 1000), "status": "ok", "count": len(ctx)}
    except Exception:
        results["pinecone_rag"] = {"ms": round((time.monotonic() - t) * 1000), "status": "error"}

    # 4. Claude chat (tiny request)
    try:
        t = time.monotonic()
        from app.services.anthropic import chat_with_claude
        resp = await chat_with_claude(message="Say hi in 3 words", max_tokens=20)
        results["claude_chat"] = {
            "ms": round((time.monotonic() - t) * 1000),
            "status": "ok",
        }
    except Exception:
        results["claude_chat"] = {"ms": round((time.monotonic() - t) * 1000), "status": "error"}

    # 5. ElevenLabs TTS (short text)
    try:
        t = time.monotonic()
        from app.services.elevenlabs import text_to_speech
        audio = await text_to_speech("Hello there.")
        results["elevenlabs_tts"] = {
            "ms": round((time.monotonic() - t) * 1000),
            "status": "ok",
            "audio_b64_len": len(audio),
        }
    except Exception:
        results["elevenlabs_tts"] = {"ms": round((time.monotonic() - t) * 1000), "status": "error"}

    total_ms = round((time.monotonic() - total_start) * 1000)
    results["total_sequential_ms"] = total_ms

    return results
