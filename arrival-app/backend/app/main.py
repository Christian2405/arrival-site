"""
Arrival Backend API Server
FastAPI app with STT, Chat, TTS, and Documents endpoints.
"""

import asyncio
import logging
import os

import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import stt, chat, tts, voice_chat, documents, analyze, queries, saved_answers

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
