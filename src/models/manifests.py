from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class StoredFileManifest(BaseModel):
    id: str
    kind: str
    path: str
    created_at: datetime
    expires_at: datetime
    session_id: str | None = None
    run_id: str | None = None
    source_document_id: str | None = None

