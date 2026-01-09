from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from src.cli.server import create_app
from src.utils.file_store import FileStore


def test_download_artifact(tmp_path: Path) -> None:
    app = create_app()
    store = FileStore(base_dir=tmp_path, ttl=timedelta(days=1))
    artifact = store.save_review("# ok", "review.md")

    from src.api import deps

    app.dependency_overrides[deps.get_file_store] = lambda: store
    client = TestClient(app)

    meta = client.get(f"/api/artifacts/{artifact.manifest.id}")
    assert meta.status_code == 200

    resp = client.get(f"/api/artifacts/{artifact.manifest.id}/download")
    assert resp.status_code == 200
    assert "# ok" in resp.text
    assert "text/markdown" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")
