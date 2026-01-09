from __future__ import annotations

from src.models.enums import Mode
from src.prompt.registry import get_prompt_text


def test_get_prompt_text_for_all_modes() -> None:
    for mode in Mode:
        text = get_prompt_text(mode)
        assert isinstance(text, str)
        assert text.strip() != ""
