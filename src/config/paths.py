from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_project_config_path() -> Path:
    return get_repo_root() / "config.yaml"


def get_global_config_path() -> Path:
    return Path.home() / ".review-analysis-agent" / "config.yaml"
