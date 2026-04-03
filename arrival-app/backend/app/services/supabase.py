"""
Supabase service — Storage, documents, and query logging operations.
Matches the website's storage path pattern and uses the documents table
as the source of truth (not raw Storage listing).
Uses shared httpx clients for connection pooling.
"""

import logging
import time
import httpx

from app import config

logger = logging.getLogger(__name__)

# Shared client — reuses TCP+TLS connections to Supabase
_client: httpx.AsyncClient | None = None


def _get_client(timeout: float = 15.0) -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=timeout)
    return _client


def _storage_headers() -> dict:
    """Service role headers for Storage operations."""
    return {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
    }


def _db_headers(user_token: str) -> dict:
    """User-scoped headers for DB operations (respects RLS)."""
    return {
        "apikey": config.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def upload_document(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user_id: str,
    user_token: str,
    category: str = "manufacturer_manuals",
    team_id: str | None = None,
) -> dict:
    """
    Upload a document to Supabase Storage AND insert into the documents table.
    Uses the same path pattern as the website: {user_id}/{timestamp}_{filename}
    """
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase credentials not configured.")

    # Build storage path (matches website pattern from dashboard.js)
    timestamp = int(time.time() * 1000)
    storage_path = f"{user_id}/{timestamp}_{filename}"
    storage_url = f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_STORAGE_BUCKET}/{storage_path}"

    client = _get_client(timeout=60.0)

    # 1. Upload to Storage (service role for storage access)
    upload_resp = await client.post(
        storage_url,
        headers={
            **_storage_headers(),
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        content=file_bytes,
    )
    upload_resp.raise_for_status()

    # 2. Insert into documents table (user token for RLS)
    doc_row = {
        "uploaded_by": user_id,
        "file_name": filename,
        "file_type": content_type,
        "file_size": len(file_bytes),
        "storage_path": storage_path,
        "category": category,
        "status": "processing",
    }
    if team_id:
        doc_row["team_id"] = team_id

    try:
        db_resp = await client.post(
            f"{config.SUPABASE_URL}/rest/v1/documents",
            headers=_db_headers(user_token),
            json=doc_row,
        )
        db_resp.raise_for_status()
    except Exception as db_err:
        # Bug #9: DB insert failed after storage upload — rollback the storage file
        logger.warning(f"[supabase] DB insert failed, rolling back storage upload: {db_err}")
        try:
            await client.request(
                "DELETE",
                f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_STORAGE_BUCKET}/{storage_path}",
                headers=_storage_headers(),
            )
        except Exception as rollback_err:
            logger.warning(f"[supabase] Storage rollback also failed: {rollback_err}")
        raise db_err

    inserted = db_resp.json()

    # Return the first (and only) inserted row
    row = inserted[0] if isinstance(inserted, list) else inserted

    # Kick off indexing as a background task — upload response returns immediately
    import asyncio
    from app.routers.documents import _run_indexing_background
    asyncio.create_task(_run_indexing_background(
        document_id=row.get("id", ""),
        user_id=user_id,
        storage_path=storage_path,
        team_id=team_id,
    ))

    return {
        "id": row.get("id", storage_path),
        "filename": filename,
        "storage_path": storage_path,
        "size": len(file_bytes),
        "content_type": content_type,
        "category": category,
        "created_at": row.get("created_at", ""),
    }


async def list_documents(
    user_id: str,
    user_token: str,
    include_team: bool = True,
) -> list[dict]:
    """
    List documents from the documents table.
    RLS policies handle access control: user sees their own docs + team docs.
    """
    if not config.SUPABASE_URL:
        raise ValueError("Supabase credentials not configured.")

    # Query documents table with user's JWT — RLS filters automatically
    # Personal docs: uploaded_by = user_id
    # Team docs: team_id in user's active teams (RLS handles this)
    params = {
        "select": "*",
        "order": "created_at.desc",
        "limit": "200",
    }

    if not include_team:
        # Only personal docs
        params["uploaded_by"] = f"eq.{user_id}"

    client = _get_client()
    resp = await client.get(
        f"{config.SUPABASE_URL}/rest/v1/documents",
        headers=_db_headers(user_token),
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


async def delete_document(
    user_id: str,
    document_id: str,
    user_token: str,
) -> bool:
    """
    Delete a document from both the documents table and Storage.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase credentials not configured.")

    client = _get_client()

    # 1. Get the document row to find storage_path
    get_resp = await client.get(
        f"{config.SUPABASE_URL}/rest/v1/documents",
        headers=_db_headers(user_token),
        params={"id": f"eq.{document_id}", "select": "storage_path,uploaded_by,team_id"},
    )
    get_resp.raise_for_status()
    rows = get_resp.json()

    if not rows:
        raise ValueError("Document not found")

    doc = rows[0]

    # 2. Delete from Storage (service role)
    if doc.get("storage_path"):
        try:
            storage_del_resp = await client.request(
                "DELETE",
                f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_STORAGE_BUCKET}",
                headers={**_storage_headers(), "Content-Type": "application/json"},
                json={"prefixes": [doc["storage_path"]]},
            )
            storage_del_resp.raise_for_status()
        except Exception as storage_err:
            # Don't fail the whole delete if storage file is already gone,
            # but log it so we can debug orphaned files
            logger.warning(f"[supabase] Storage delete failed (continuing): {storage_err}")

    # 3. Delete from documents table (user token for RLS)
    del_resp = await client.delete(
        f"{config.SUPABASE_URL}/rest/v1/documents",
        headers=_db_headers(user_token),
        params={"id": f"eq.{document_id}"},
    )
    del_resp.raise_for_status()

    # Remove vectors from RAG index (non-blocking)
    try:
        from app.services.rag import delete_document_vectors
        await delete_document_vectors(document_id, user_id, team_id=doc.get("team_id"))
    except Exception as e:
        logger.warning(f"[supabase] RAG vector delete failed (non-blocking): {e}")

    return True


# ============================================
# QUERY LOGGING (Team Activity)
# ============================================

def _service_db_headers() -> dict:
    """Service role headers for DB operations (bypasses RLS)."""
    return {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


async def log_query(
    user_id: str,
    question: str,
    response: str | None = None,
    source: str | None = None,
    confidence: str | None = None,
    has_image: bool = False,
    team_id: str | None = None,
    mode: str | None = None,
    rag_chunks_used: list[dict] | None = None,
    response_time_ms: int | None = None,
) -> None:
    """
    Log a chat query to the queries table for team activity tracking + data flywheel.
    Uses service role to bypass RLS (backend is trusted).
    Non-blocking — failures are silently logged.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        return

    row = {
        "user_id": user_id,
        "question": question[:500],  # Cap at 500 chars
        "has_image": has_image,
    }
    if response:
        row["response"] = response[:2000]  # Cap at 2000 chars
    if source:
        row["source"] = source
    if confidence:
        row["confidence"] = confidence
    if team_id:
        row["team_id"] = team_id
    if mode:
        row["mode"] = mode
    if rag_chunks_used:
        row["rag_chunks_used"] = rag_chunks_used
    if response_time_ms is not None:
        row["response_time_ms"] = response_time_ms

    try:
        client = _get_client()
        resp = await client.post(
            f"{config.SUPABASE_URL}/rest/v1/queries",
            headers=_service_db_headers(),
            json=row,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[supabase] Query log failed (non-blocking): {e}")


async def get_user_team_id(user_id: str) -> str | None:
    """Look up the user's active team_id from team_members table."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        return None

    try:
        t0 = time.monotonic()
        client = _get_client()
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/team_members",
            headers=_service_db_headers(),
            params={
                "user_id": f"eq.{user_id}",
                "status": "eq.active",
                "select": "team_id",
                "limit": "1",
            },
        )
        resp.raise_for_status()
        rows = resp.json()
        logger.info(f"[supabase] Team lookup in {time.monotonic()-t0:.2f}s")
        if rows:
            return rows[0].get("team_id")
    except Exception as e:
        logger.warning(f"[supabase] Team lookup failed: {e}")

    return None


async def get_team_queries(
    team_id: str,
    user_token: str,
    limit: int = 50,
) -> list[dict]:
    """
    Get recent queries for a team (for activity feed / stats).
    Uses user token so RLS applies.
    """
    if not config.SUPABASE_URL:
        return []

    try:
        client = _get_client()
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/queries",
            headers=_db_headers(user_token),
            params={
                "team_id": f"eq.{team_id}",
                "select": "id,user_id,question,source,confidence,has_image,created_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"[supabase] Get team queries failed: {e}")
        return []
