from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast


def _docmind_parse_sync(path_str: str) -> str:
    import importlib
    from pathlib import Path
    from typing import Any, cast

    path = Path(path_str)
    aili_doc_parser = cast(Any, importlib.import_module("src.utils.aili_doc_parser"))
    doc_parser_type = cast(type[Any], aili_doc_parser.DocParser)
    parser = doc_parser_type()
    task_id = parser.submit_job(str(path), file_name=path.name)
    if not task_id:
        raise ValueError("DocMind submit failed")
    ok = parser.wait_for_completion(task_id, poll_interval=2)
    if not ok:
        raise ValueError("DocMind parse failed")
    parts: list[str] = []
    for layouts in parser.collect_results_incrementally(task_id, layout_step_size=10):
        parts.append(parser.generate_markdown(layouts))
    return "".join(parts)


def _docmind_parse_via_subprocess(path_str: str) -> str:
    import multiprocessing

    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)

    proc = ctx.Process(target=_docmind_parse_worker, args=(child_conn, path_str))
    proc.start()
    result = parent_conn.recv()
    proc.join()
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[0], bool)
        and isinstance(result[1], str)
    ):
        ok = cast(bool, result[0])
        payload = cast(str, result[1])
        if ok:
            return payload
        raise ValueError(payload)
    raise ValueError("Invalid DocMind worker result")


def _docmind_parse_worker(conn: Any, path_str: str) -> None:
    try:
        conn.send((True, _docmind_parse_sync(path_str)))
    except Exception as e:
        conn.send((False, str(e)))
    finally:
        conn.close()


class DocumentParser:
    async def parse(self, path: Path) -> str:
        if path.suffix.lower() in {".md", ".txt"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if os.getenv("DOCMIND_ENABLED") != "1":
            raise ValueError("DocMind parsing is not enabled")
        return await self._parse_with_docmind(path)

    async def _parse_with_docmind(self, path: Path) -> str:
        import asyncio
        import threading

        if threading.current_thread() is threading.main_thread():
            return self._parse_with_docmind_sync(path)
        return await asyncio.to_thread(_docmind_parse_via_subprocess, str(path))

    def _parse_with_docmind_sync(self, path: Path) -> str:
        return _docmind_parse_sync(str(path))
