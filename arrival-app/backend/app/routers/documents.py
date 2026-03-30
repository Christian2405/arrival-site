"""
Documents router — upload, list, delete, and index documents via Supabase.
All endpoints require authentication (JWT).
Uses the documents table as source of truth (matches website).
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Query
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.supabase import upload_document, list_documents, delete_document
from app.services.rag import index_document, DocumentTooShortError, PineconeQuotaError
from app.services.usage import check_document_limit
from app import config

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentResponse(BaseModel):
    id: str
    filename: str
    storage_path: str
    size: int
    content_type: str
    category: str
    created_at: str


class DocumentListResponse(BaseModel):
    documents: list[dict]


class DeleteResponse(BaseModel):
    success: bool
    message: str


class IndexRequest(BaseModel):
    document_id: str | None = None  # May be null if Supabase RLS blocks .select() after insert
    storage_path: str
    team_id: str | None = None  # Bug #1: Optional team_id for team document indexing


class IndexResponse(BaseModel):
    success: bool
    chunks_indexed: int
    message: str


@router.post("/upload", response_model=DocumentResponse)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("manufacturer_manuals"),
    team_id: str | None = Form(None),
):
    """
    Upload a document (PDF, image, manual) to Supabase.
    Stores in Storage AND records in documents table.
    """
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx", ".dwg", ".dxf"}

    try:
        user = await get_current_user(request)
        user_id = user["user_id"]
        user_token = user["token"]

        # Check document limit (only for personal uploads, not team)
        if not team_id:
            doc_usage = await check_document_limit(user_id)
            if not doc_usage["allowed"]:
                raise HTTPException(
                    status_code=403,
                    detail="Document limit reached. Upgrade for more.",
                )

        # Validate file type by extension
        filename = file.filename or "untitled"
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        if len(file_bytes) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")

        result = await upload_document(
            file_bytes=file_bytes,
            filename=file.filename or "untitled",
            content_type=file.content_type or "application/octet-stream",
            user_id=user_id,
            user_token=user_token,
            category=category,
            team_id=team_id,
        )

        return DocumentResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_docs(
    request: Request,
    include_team: bool = Query(True, description="Include team documents"),
):
    """
    List documents from the documents table.
    RLS handles access control — user sees own docs + team docs.
    """
    try:
        user = await get_current_user(request)
        docs = await list_documents(
            user_id=user["user_id"],
            user_token=user["token"],
            include_team=include_team,
        )
        return DocumentListResponse(documents=docs)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_doc(document_id: str, request: Request):
    """
    Delete a document by its ID (UUID from documents table).
    RLS ensures user can only delete their own documents.
    """
    try:
        user = await get_current_user(request)
        await delete_document(
            user_id=user["user_id"],
            document_id=document_id,
            user_token=user["token"],
        )
        return DeleteResponse(success=True, message="Document deleted")

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.post("/index-document", response_model=IndexResponse)
async def index_doc(body: IndexRequest, request: Request):
    """
    Trigger RAG indexing for a document already uploaded to Supabase Storage.
    Called by the website dashboards after direct-to-Supabase uploads.
    Downloads the file from Storage, extracts text, chunks, and upserts to Pinecone.
    """
    try:
        user = await get_current_user(request)
        user_id = user["user_id"]
        user_token = user["token"]

        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
            return IndexResponse(success=False, chunks_indexed=0, message="Supabase not configured")

        if not config.PINECONE_API_KEY:
            return IndexResponse(success=False, chunks_indexed=0, message="Pinecone not configured")

        # Look up the document from the DB to verify ownership
        import httpx
        doc_resp = None
        if body.document_id:
            doc_resp = await _lookup_document(body.document_id, user_token)
        if doc_resp is None:
            # Fallback: look up by storage_path (handles null document_id from RLS issues)
            doc_resp = await _lookup_document_by_path(body.storage_path, user_token)
        if doc_resp is None:
            raise HTTPException(
                status_code=403,
                detail="Document not found or you don't have access to it"
            )

        # Use the DB-sourced values as source of truth
        trusted_storage_path = doc_resp["storage_path"]
        document_id = doc_resp["id"]
        doc_team_id = doc_resp.get("team_id") or body.team_id
        if doc_resp.get("team_id"):
            doc_team_id = doc_resp["team_id"]

        # Validation — storage_path must not contain path traversal
        if ".." in trusted_storage_path:
            raise HTTPException(status_code=400, detail="Invalid storage path")

        # Download the file from Supabase Storage
        storage_url = (
            f"{config.SUPABASE_URL}/storage/v1/object/"
            f"{config.SUPABASE_STORAGE_BUCKET}/{trusted_storage_path}"
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                storage_url,
                headers={
                    "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                },
            )
            resp.raise_for_status()
            file_bytes = resp.content

        # Guess content type from filename
        filename = trusted_storage_path.split("/")[-1]
        # Strip the timestamp prefix (e.g., "1700000000000_manual.pdf" -> "manual.pdf")
        if "_" in filename:
            filename = filename.split("_", 1)[1]

        content_type = "application/octet-stream"
        lower = filename.lower()
        if lower.endswith(".pdf"):
            content_type = "application/pdf"
        elif lower.endswith((".txt", ".md", ".csv")):
            content_type = "text/plain"
        elif lower.endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        # Index via RAG pipeline
        chunks = await index_document(
            document_id=document_id,
            user_id=user_id,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
            team_id=doc_team_id,
        )

        return IndexResponse(
            success=True,
            chunks_indexed=chunks,
            message=f"Indexed {chunks} chunks from {filename}",
        )

    except HTTPException:
        raise
    except DocumentTooShortError as e:
        return IndexResponse(success=False, chunks_indexed=0, message=str(e))
    except PineconeQuotaError as e:
        logger.error(f"[index-document] Pinecone quota exhausted: {e}")
        raise HTTPException(status_code=507, detail=str(e))
    except Exception as e:
        logger.error(f"[index-document] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


async def _lookup_document(document_id: str, user_token: str) -> dict | None:
    """
    Look up a document from the documents table using the user's JWT.
    RLS ensures the user can only see their own docs or team docs.
    Returns the document row dict, or None if not found / not accessible.
    Bug #3: Ownership check via RLS.
    Bug #4: Returns trusted storage_path from DB.
    """
    import httpx
    if not config.SUPABASE_URL:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/documents",
                headers={
                    "apikey": config.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {user_token}",
                    "Content-Type": "application/json",
                },
                params={
                    "id": f"eq.{document_id}",
                    "select": "id,storage_path,uploaded_by,team_id",
                    "limit": "1",
                },
            )
            resp.raise_for_status()
            rows = resp.json()
            if rows:
                return rows[0]
    except Exception as e:
        logger.warning(f"[documents] Document lookup failed: {e}")

    return None


async def _lookup_document_by_path(storage_path: str, user_token: str) -> dict | None:
    """
    Look up a document by storage_path when document_id is null.
    Handles the case where Supabase RLS blocks .select() after .insert(),
    so the dashboard doesn't get the document ID back.
    """
    import httpx
    if not config.SUPABASE_URL:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/documents",
                headers={
                    "apikey": config.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {user_token}",
                    "Content-Type": "application/json",
                },
                params={
                    "storage_path": f"eq.{storage_path}",
                    "select": "id,storage_path,uploaded_by,team_id",
                    "limit": "1",
                },
            )
            resp.raise_for_status()
            rows = resp.json()
            if rows:
                return rows[0]
    except Exception as e:
        logger.warning(f"[documents] Document lookup by path failed: {e}")

    return None
