"""
Arrival Backend API Server
FastAPI app with STT, Chat, TTS, and Documents endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import stt, chat, tts, documents

app = FastAPI(
    title="Arrival API",
    version="2.0.0",
    description="AI voice & camera assistant for trade workers",
)

# CORS — allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(stt.router, prefix="/api", tags=["Speech-to-Text"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(tts.router, prefix="/api", tags=["Text-to-Speech"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])


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
