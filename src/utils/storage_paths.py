from __future__ import annotations

from pathlib import Path


def get_datas_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "datas"


def get_documents_dir() -> Path:
    return get_datas_dir() / "documents"


def get_reviews_dir() -> Path:
    return get_datas_dir() / "reviews"


def get_manifests_dir() -> Path:
    return get_datas_dir() / "manifests"

