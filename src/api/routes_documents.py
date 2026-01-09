from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.api.deps import get_file_store
from src.utils.file_store import FileStore

router = APIRouter(prefix="/api")


class UploadDocumentResponse(BaseModel):
    document_id: str
    expires_at: str


@router.post("/documents", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    store: FileStore = Depends(get_file_store),
) -> UploadDocumentResponse:
    """Upload a document and store it with TTL.

    Args:
        file: Uploaded file.

    Returns:
        Document metadata.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="filename is required")
    result = store.save_document(file.file, file.filename, file.content_type)
    return UploadDocumentResponse(
        document_id=result.manifest.id,
        expires_at=result.manifest.expires_at.isoformat(),
    )
