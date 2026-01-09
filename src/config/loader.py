from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from src.config.paths import get_global_config_path, get_project_config_path
from src.config.schema import AppConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML root type: {type(data)}")
    return data


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(base)
    for k, v in override.items():
        existing = out.get(k)
        if isinstance(v, dict) and isinstance(existing, dict):
            out[k] = _merge_dicts(existing, v)
        else:
            out[k] = v
    return out


def _resolve_env(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("$") and len(value) > 1:
        return os.getenv(value[1:])
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


def load_raw_config() -> dict[str, Any]:
    global_cfg = _read_yaml(get_global_config_path())
    project_cfg = _read_yaml(get_project_config_path())
    merged = _merge_dicts(global_cfg, project_cfg)
    resolved = _resolve_env(merged)
    if not isinstance(resolved, dict):
        raise ValueError("Config root must be a mapping")
    return resolved


def get_config_section(keys: list[str]) -> dict[str, Any] | None:
    data: Any = load_raw_config()
    for key in keys:
        if not isinstance(data, dict):
            return None
        if key not in data:
            return None
        data = data[key]
    if isinstance(data, dict):
        return data
    return None


def load_config() -> AppConfig:
    raw = load_raw_config()
    return AppConfig.model_validate(raw)
