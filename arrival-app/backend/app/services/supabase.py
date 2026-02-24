"""
Supabase service — Storage + documents table operations.
Matches the website's storage path pattern and uses the documents table
as the source of truth (not raw Storage listing).
"""

import time
import httpx

from app import config


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

    async with httpx.AsyncClient(timeout=60.0) as client:
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
            "status": "ready",
        }
        if team_id:
            doc_row["team_id"] = team_id

        db_resp = await client.post(
            f"{config.SUPABASE_URL}/rest/v1/documents",
            headers=_db_headers(user_token),
            json=doc_row,
        )
        db_resp.raise_for_status()
        inserted = db_resp.json()

    # Return the first (and only) inserted row
    row = inserted[0] if isinstance(inserted, list) else inserted

    # Index for RAG (non-blocking — upload succeeds even if indexing fails)
    try:
        from app.services.rag import index_document
        await index_document(
            document_id=row.get("id", ""),
            user_id=user_id,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
        )
    except Exception as e:
        print(f"[supabase] RAG indexing failed (non-blocking): {e}")

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

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/documents",
            headers=_db_headers(user_token),
            params=params,
        )
        resp.raise_for_status()
        rows = resp.json()

    return rows


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

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Get the document row to find storage_path
        get_resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/documents",
            headers=_db_headers(user_token),
            params={"id": f"eq.{document_id}", "select": "storage_path,uploaded_by"},
        )
        get_resp.raise_for_status()
        rows = get_resp.json()

        if not rows:
            raise ValueError("Document not found")

        doc = rows[0]

        # 2. Delete from Storage (service role)
        if doc.get("storage_path"):
            del_storage = await client.request(
                "DELETE",
                f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_STORAGE_BUCKET}",
                headers={**_storage_headers(), "Content-Type": "application/json"},
                json={"prefixes": [doc["storage_path"]]},
            )
            # Don't fail if storage delete errors (file may already be gone)

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
        await delete_document_vectors(document_id, user_id)
    except Exception as e:
        print(f"[supabase] RAG vector delete failed (non-blocking): {e}")

    return True
