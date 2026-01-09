from __future__ import annotations

from pathlib import Path

import yaml
from _pytest.monkeypatch import MonkeyPatch

from src.config import loader


def test_merge_and_env_resolution(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    global_path = tmp_path / "global.yaml"
    project_path = tmp_path / "project.yaml"
    global_path.write_text(
        yaml.safe_dump(
            {
                "models": {
                    "chat_model": {
                        "model": "gpt-test",
                        "api_key": "$TEST_KEY",
                        "temperature": 0.2,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    project_path.write_text(
        yaml.safe_dump(
            {
                "models": {
                    "chat_model": {
                        "temperature": 0.7,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("TEST_KEY", "abc")
    monkeypatch.setattr(loader, "get_global_config_path", lambda: global_path)
    monkeypatch.setattr(loader, "get_project_config_path", lambda: project_path)

    raw = loader.load_raw_config()
    assert raw["models"]["chat_model"]["api_key"] == "abc"
    assert raw["models"]["chat_model"]["temperature"] == 0.7
