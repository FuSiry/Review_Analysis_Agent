from __future__ import annotations

import asyncio
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from _pytest.monkeypatch import MonkeyPatch

from src.utils.document_parser import DocumentParser


def test_document_parser_reads_markdown(tmp_path: Path) -> None:
    p = tmp_path / "a.md"
    p.write_text("# hi", encoding="utf-8")

    parser = DocumentParser()
    out = asyncio.run(parser.parse(p))
    assert out == "# hi"


def test_document_parser_requires_docmind_for_non_text(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    p = tmp_path / "a.pdf"
    p.write_bytes(b"%PDF")

    monkeypatch.delenv("DOCMIND_ENABLED", raising=False)
    parser = DocumentParser()

    with pytest.raises(ValueError, match="DocMind parsing is not enabled"):
        asyncio.run(parser.parse(p))


def test_document_parser_docmind_path_joins_markdown(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    p = tmp_path / "a.pdf"
    p.write_bytes(b"%PDF")

    mod = types.ModuleType("src.utils.aili_doc_parser")

    class FakeDocParser:
        def submit_job(
            self, file_path: str, file_name: str | None = None
        ) -> str | None:
            return "tid"

        def wait_for_completion(self, task_id: str, poll_interval: int = 5) -> bool:
            return True

        def collect_results_incrementally(
            self, task_id: str, layout_step_size: int = 10
        ) -> Iterator[list[dict[str, str]]]:
            yield [{"content": "a"}]
            yield [{"content": "b"}]

        def generate_markdown(self, layouts: list[object]) -> str:
            out = ""
            for it in layouts:
                if isinstance(it, dict) and isinstance(it.get("content"), str):
                    out += it["content"]
            return out

    mod_any = cast(Any, mod)
    mod_any.DocParser = FakeDocParser
    monkeypatch.setenv("DOCMIND_ENABLED", "1")
    monkeypatch.setitem(sys.modules, "src.utils.aili_doc_parser", mod)

    parser = DocumentParser()
    out = asyncio.run(parser.parse(p))
    assert out == "ab"
