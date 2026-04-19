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

from app.routers import stt, chat, tts, voice_chat, voice_ws, documents, analyze, queries, saved_answers, usage, feedback, job_context, error_codes_api, account, livekit_token, admin_feedback, spatial

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


async def _seed_knowledge_base():
    """One-time task: index knowledge docs into Pinecone global_knowledge.
    Scans knowledge/ root and knowledge/building_codes/ for .md files.
    Runs on startup — skips if Pinecone isn't configured."""
    from app import config
    if not config.PINECONE_API_KEY:
        logger.info("[seed] Pinecone not configured — skipping knowledge seed")
        return

    from pathlib import Path
    knowledge_root = Path(__file__).resolve().parent.parent / "knowledge"
    if not knowledge_root.exists():
        logger.info("[seed] No knowledge/ directory — skipping")
        return

    from app.services.rag import extract_text_from_file, chunk_text_smart, chunk_text, _get_pinecone_index
    index = _get_pinecone_index()
    if not index:
        return

    # Collect .md files from root and all subdirectories
    files = sorted(knowledge_root.rglob("*.md"))
    if not files:
        return

    logger.info(f"[seed] Indexing {len(files)} knowledge docs into global_knowledge...")
    total = 0

    for filepath in files:
        filename = filepath.name
        doc_id = f"global_{filename.replace(' ', '_').replace('.', '_')}"

        file_bytes = filepath.read_bytes()
        text, _ = extract_text_from_file(file_bytes, "text/markdown", filename)
        if not text:
            continue

        chunks = chunk_text_smart(text) or chunk_text(text)
        if not chunks:
            continue

        records = []
        for i, chunk in enumerate(chunks):
            records.append({
                "_id": f"{doc_id}_{i}",
                "text": chunk,
                "document_id": doc_id,
                "user_id": "system",
                "filename": filename,
                "chunk_index": i,
            })

        try:
            for batch_start in range(0, len(records), 96):
                batch = records[batch_start:batch_start + 96]
                await asyncio.to_thread(index.upsert_records, namespace="global_knowledge", records=batch)
            total += len(records)
            logger.info(f"[seed] ✓ {filename}: {len(chunks)} chunks")
        except Exception as e:
            logger.warning(f"[seed] Failed to index {filename}: {e}")

    logger.info(f"[seed] Done — {total} total chunks indexed")


async def _reindex_stuck_documents():
    """
    On startup: find any documents stuck in 'processing' or 'index_failed' and re-index them.
    This means users never need to retry manually — the backend handles it automatically.
    Waits 30s after startup so the server is fully ready before hitting Pinecone/Supabase.
    """
    from app import config
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY or not config.PINECONE_API_KEY:
        return

    await asyncio.sleep(30)  # Let the server finish booting

    logger.info("[reindex] Checking for stuck documents...")
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/documents",
                headers={
                    "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                },
                params={
                    "status": "in.(processing,index_failed)",
                    "select": "id,storage_path,uploaded_by,team_id,file_name",
                    "created_at": f"lt.{cutoff}",
                    "order": "created_at.asc",
                    "limit": "50",
                },
            )
            resp.raise_for_status()
            stuck_docs = resp.json()

        if not stuck_docs:
            logger.info("[reindex] No stuck documents found")
            return

        logger.info(f"[reindex] Found {len(stuck_docs)} stuck document(s) — re-indexing...")
        from app.services.rag import index_document

        for doc in stuck_docs:
            doc_id = doc["id"]
            storage_path = doc["storage_path"]
            user_id = doc["uploaded_by"]
            team_id = doc.get("team_id")
            filename = storage_path.split("/")[-1]
            if "_" in filename:
                filename = filename.split("_", 1)[1]

            try:
                # Download file from Supabase Storage
                async with httpx.AsyncClient(timeout=60.0) as client:
                    dl = await client.get(
                        f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_STORAGE_BUCKET}/{storage_path}",
                        headers={
                            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                            "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                        },
                    )
                    dl.raise_for_status()
                    file_bytes = dl.content

                # Guess content type
                lower = filename.lower()
                if lower.endswith(".pdf"):
                    content_type = "application/pdf"
                elif lower.endswith(".docx"):
                    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                else:
                    content_type = "text/plain"

                chunks = await index_document(
                    document_id=doc_id,
                    user_id=user_id,
                    filename=filename,
                    file_bytes=file_bytes,
                    content_type=content_type,
                    team_id=team_id,
                )

                # Mark as indexed
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.patch(
                        f"{config.SUPABASE_URL}/rest/v1/documents",
                        headers={
                            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                            "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                            "Content-Type": "application/json",
                            "Prefer": "return=minimal",
                        },
                        params={"id": f"eq.{doc_id}"},
                        json={"status": "ready"},
                    )
                logger.info(f"[reindex] ✓ {filename} — {chunks} chunks")

            except Exception as e:
                logger.warning(f"[reindex] ✗ {filename}: {e}")
                # Mark as failed so the Retry button shows in the dashboard
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.patch(
                            f"{config.SUPABASE_URL}/rest/v1/documents",
                            headers={
                                "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                                "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                                "Content-Type": "application/json",
                                "Prefer": "return=minimal",
                            },
                            params={"id": f"eq.{doc_id}"},
                            json={"status": "index_failed"},
                        )
                except Exception:
                    pass

    except Exception as e:
        logger.warning(f"[reindex] Startup reindex failed: {e}")


async def _smoke_test_anthropic_models():
    """
    Verify configured Anthropic models actually exist before serving traffic.
    A bad model name silently 404s every request (which is what broke Job Mode
    on April 10 with the fake 'claude-sonnet-4-6'). This logs SUCCESS or
    FAILURE prominently so deploy regressions are caught immediately.

    Does NOT raise — we don't want to take down the whole backend just because
    of a model issue. The errors are loud enough in Render logs.
    """
    try:
        from app import config
        import anthropic

        if not config.ANTHROPIC_API_KEY:
            logger.warning("[model-smoke] Skipped — ANTHROPIC_API_KEY not set")
            return

        # Test each unique configured model exactly once
        models_to_test = list(set([
            config.ANTHROPIC_MODEL,
            config.ANTHROPIC_VOICE_MODEL,
            config.ANTHROPIC_VISION_MODEL,
        ]))

        client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

        for model_name in models_to_test:
            try:
                await client.messages.create(
                    model=model_name,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}],
                )
                logger.info(f"[model-smoke] OK — {model_name}")
            except anthropic.NotFoundError as e:
                logger.error(
                    f"[model-smoke] *** MODEL NOT FOUND *** {model_name} — "
                    f"every LLM call will 404. Update Render env var or app/config.py. Error: {e}"
                )
            except Exception as e:
                logger.error(f"[model-smoke] {model_name} — call failed: {type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"[model-smoke] Unexpected error during smoke test: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — launches keep-alive + seeds knowledge base."""
    keep_alive_task = asyncio.create_task(_keep_alive())
    seed_task = asyncio.create_task(_seed_knowledge_base())
    reindex_task = asyncio.create_task(_reindex_stuck_documents())
    smoke_task = asyncio.create_task(_smoke_test_anthropic_models())
    yield
    keep_alive_task.cancel()
    seed_task.cancel()
    reindex_task.cancel()
    smoke_task.cancel()
    for t in (keep_alive_task, seed_task, reindex_task, smoke_task):
        try:
            await t
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Arrival API",
    version="1.0.0",
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
app.include_router(job_context.router, prefix="/api", tags=["Job Context"])
app.include_router(error_codes_api.router, prefix="/api", tags=["Error Codes"])
app.include_router(account.router, prefix="/api", tags=["Account"])
app.include_router(voice_ws.router, prefix="/ws", tags=["Voice WebSocket"])
app.include_router(livekit_token.router, prefix="/api", tags=["LiveKit"])
app.include_router(admin_feedback.router, prefix="/api", tags=["Admin"])
app.include_router(spatial.router, tags=["Spatial Intelligence"])


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
        "version": "1.0.0",
        "service": "Arrival API",
    }


@app.get("/")
async def root():
    return {"status": "ok", "service": "Arrival API", "version": "1.0.0"}


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
