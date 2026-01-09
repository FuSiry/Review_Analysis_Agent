from __future__ import annotations

from pathlib import Path

from src.models.enums import Mode


def get_prompt_text(mode: Mode) -> str:
    templates_dir = Path(__file__).resolve().parent / "templates"
    path = templates_dir / f"{mode.value}.md"
    return path.read_text(encoding="utf-8")

