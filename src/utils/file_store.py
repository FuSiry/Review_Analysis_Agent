from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO

from src.models.manifests import StoredFileManifest


@dataclass(frozen=True)
class StoreResult:
    manifest: StoredFileManifest


class FileStore:
    def __init__(self, base_dir: Path, ttl: timedelta) -> None:
        self._base_dir = base_dir
        self._ttl = ttl
        self._documents_dir = base_dir / "documents"
        self._reviews_dir = base_dir / "reviews"
        self._manifests_dir = base_dir / "manifests"
        self._documents_dir.mkdir(parents=True, exist_ok=True)
        self._reviews_dir.mkdir(parents=True, exist_ok=True)
        self._manifests_dir.mkdir(parents=True, exist_ok=True)

    def save_document(
        self,
        fileobj: BinaryIO,
        filename: str,
        content_type: str | None,
        session_id: str | None = None,
    ) -> StoreResult:
        now = datetime.utcnow()
        expires_at = now + self._ttl
        doc_id = uuid.uuid4().hex
        path = self._documents_dir / f"{doc_id}__{filename}"
        with open(path, "wb") as f:
            f.write(fileobj.read())
        manifest = StoredFileManifest(
            id=doc_id,
            kind="document",
            path=str(path),
            created_at=now,
            expires_at=expires_at,
            session_id=session_id,
        )
        self._write_manifest(manifest)
        return StoreResult(manifest=manifest)

    def save_review(
        self,
        markdown: str,
        filename: str,
        session_id: str | None = None,
        run_id: str | None = None,
        source_document_id: str | None = None,
    ) -> StoreResult:
        now = datetime.utcnow()
        expires_at = now + self._ttl
        artifact_id = uuid.uuid4().hex
        safe_name = filename if filename.endswith(".md") else f"{filename}.md"
        path = self._reviews_dir / f"{artifact_id}__{safe_name}"
        path.write_text(markdown, encoding="utf-8")
        manifest = StoredFileManifest(
            id=artifact_id,
            kind="review",
            path=str(path),
            created_at=now,
            expires_at=expires_at,
            session_id=session_id,
            run_id=run_id,
            source_document_id=source_document_id,
        )
        self._write_manifest(manifest)
        return StoreResult(manifest=manifest)

    def get_manifest(self, kind: str, file_id: str) -> StoredFileManifest | None:
        manifest_path = self._manifests_dir / f"{kind}__{file_id}.json"
        if not manifest_path.exists():
            return None
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return StoredFileManifest.model_validate(data)

    def cleanup_expired(self, now: datetime | None = None) -> int:
        now_ = now or datetime.utcnow()
        removed = 0
        for path in self._manifests_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            manifest = StoredFileManifest.model_validate(data)
            if manifest.expires_at <= now_:
                Path(manifest.path).unlink(missing_ok=True)
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    def _write_manifest(self, manifest: StoredFileManifest) -> None:
        path = self._manifests_dir / f"{manifest.kind}__{manifest.id}.json"
        path.write_text(
            json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

