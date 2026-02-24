"""
Documents router — upload, list, delete documents via Supabase.
All endpoints require authentication (JWT).
Uses the documents table as source of truth (matches website).
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Query
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.supabase import upload_document, list_documents, delete_document

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


@router.post("/upload", response_model=DocumentResponse)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("equipment_manuals"),
    team_id: str | None = Form(None),
):
    """
    Upload a document (PDF, image, manual) to Supabase.
    Stores in Storage AND records in documents table.
    """
    try:
        user = await get_current_user(request)
        user_id = user["user_id"]
        user_token = user["token"]

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
