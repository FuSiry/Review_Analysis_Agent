from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from src.cli.server import create_app
from src.utils.file_store import FileStore


def test_upload_document(tmp_path: Path) -> None:
    app = create_app()
    store = FileStore(base_dir=tmp_path, ttl=timedelta(days=1))

    from src.api import deps

    app.dependency_overrides[deps.get_file_store] = lambda: store
    client = TestClient(app)

    resp = client.post(
        "/api/documents",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "document_id" in data
    assert "expires_at" in data

