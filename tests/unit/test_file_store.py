from __future__ import annotations

import io
from datetime import datetime, timedelta
from pathlib import Path

from src.utils.file_store import FileStore


def test_save_and_cleanup(tmp_path: Path) -> None:
    store = FileStore(base_dir=tmp_path, ttl=timedelta(days=1))
    doc = store.save_document(io.BytesIO(b"hello"), "a.txt", "text/plain")
    assert store.get_manifest("document", doc.manifest.id) is not None

    review = store.save_review("# hi", "r.md")
    assert store.get_manifest("review", review.manifest.id) is not None

    removed = store.cleanup_expired(now=datetime.utcnow() + timedelta(days=2))
    assert removed == 2

