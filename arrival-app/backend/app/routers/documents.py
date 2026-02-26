"""
Documents router — upload, list, delete, and index documents via Supabase.
All endpoints require authentication (JWT).
Uses the documents table as source of truth (matches website).
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Query
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.supabase import upload_document, list_documents, delete_document
from app.services.rag import index_document
from app import config

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
    document_id: str
    storage_path: str


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

        # Validate file type by extension
        import os
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

        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
            return IndexResponse(success=False, chunks_indexed=0, message="Supabase not configured")

        if not config.PINECONE_API_KEY:
            return IndexResponse(success=False, chunks_indexed=0, message="Pinecone not configured")

        # Download the file from Supabase Storage
        import httpx
        storage_url = (
            f"{config.SUPABASE_URL}/storage/v1/object/"
            f"{config.SUPABASE_STORAGE_BUCKET}/{body.storage_path}"
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
        filename = body.storage_path.split("/")[-1]
        # Strip the timestamp prefix (e.g., "1700000000000_manual.pdf" -> "manual.pdf")
        if "_" in filename:
            filename = filename.split("_", 1)[1]

        content_type = "application/octet-stream"
        lower = filename.lower()
        if lower.endswith(".pdf"):
            content_type = "application/pdf"
        elif lower.endswith((".txt", ".md", ".csv")):
            content_type = "text/plain"

        # Index via RAG pipeline
        chunks = await index_document(
            document_id=body.document_id,
            user_id=user_id,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
        )

        return IndexResponse(
            success=True,
            chunks_indexed=chunks,
            message=f"Indexed {chunks} chunks from {filename}",
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[index-document] Error: {e}")
        # Return success=False but don't error — indexing is best-effort
        return IndexResponse(success=False, chunks_indexed=0, message=str(e))
