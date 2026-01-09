from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.deps import get_file_store
from src.utils.file_store import FileStore

router = APIRouter(prefix="/api")


class ArtifactMeta(BaseModel):
    artifact_id: str
    expires_at: str


@router.get("/artifacts/{artifact_id}", response_model=ArtifactMeta)
async def get_artifact_meta(
    artifact_id: str,
    store: FileStore = Depends(get_file_store),
) -> ArtifactMeta:
    """Get artifact metadata.

    Args:
        artifact_id: Artifact identifier.

    Returns:
        Artifact metadata.
    """

    manifest = store.get_manifest("review", artifact_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="artifact not found")
    if manifest.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="artifact expired")
    return ArtifactMeta(artifact_id=manifest.id, expires_at=manifest.expires_at.isoformat())


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    store: FileStore = Depends(get_file_store),
) -> FileResponse:
    """Download a markdown artifact.

    Args:
        artifact_id: Artifact identifier.

    Returns:
        Markdown file.
    """

    manifest = store.get_manifest("review", artifact_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="artifact not found")
    if manifest.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="artifact expired")
    path = Path(manifest.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="artifact file missing")
    return FileResponse(path=path, filename=path.name, media_type="text/markdown; charset=utf-8")
