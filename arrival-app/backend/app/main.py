"""
Arrival Backend API Server
FastAPI app with STT, Chat, TTS, and Documents endpoints.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import stt, chat, tts, documents, analyze, queries, saved_answers

app = FastAPI(
    title="Arrival API",
    version="2.0.0",
    description="AI voice & camera assistant for trade workers",
)

# CORS — restrict origins in production, allow all in development
_debug = os.getenv("DEBUG", "false").lower() == "true"
_allowed_origins = (
    ["*"] if _debug else [
        "https://arrivalcompany.com",
        "https://www.arrivalcompany.com",
        "https://arrival-site.netlify.app",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(stt.router, prefix="/api", tags=["Speech-to-Text"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(tts.router, prefix="/api", tags=["Text-to-Speech"])
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
