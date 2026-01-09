from __future__ import annotations

import types
from pathlib import Path
from typing import Any, cast

from _pytest.monkeypatch import MonkeyPatch

from src.utils.aili_doc_parser import DocParser


def _new_parser() -> DocParser:
    parser = DocParser.__new__(DocParser)
    parser.endpoint = "test"
    parser.client = object()
    return parser


def test_generate_markdown_mixes_text_and_table() -> None:
    parser = _new_parser()
    layouts: list[dict[str, Any]] = [
        {"text": {"content": " hello "}},
        {
            "type": "table",
            "cells": [
                {"ysc": 0, "xsc": 0, "text": {"content": "a"}},
                {"ysc": 0, "xsc": 1, "content": "b"},
                {"ysc": 1, "xsc": 0, "text": {"text": "c"}},
            ],
        },
        {"content": "world"},
    ]

    out = parser.generate_markdown(layouts)
    assert "hello" in out
    assert "<table" in out
    assert "<td>a</td>" in out
    assert "<td>b</td>" in out
    assert "<td>c</td>" in out
    assert "world" in out


def test_collect_results_incrementally_pages_until_short_page() -> None:
    parser = _new_parser()
    pages: list[list[dict[str, Any]]] = [
        [{"content": "p1"}] * 2,
        [{"content": "p2"}] * 1,
    ]

    def fake_get_result(
        *, task_id: str, layout_num: int, layout_step_size: int
    ) -> dict[str, Any] | None:
        if not pages:
            return None
        return {"layouts": pages.pop(0)}

    parser_any = cast(Any, parser)
    parser_any.get_result = fake_get_result

    got = list(parser.collect_results_incrementally("t", layout_step_size=2))
    assert [len(x) for x in got] == [2, 1]


def test_wait_for_completion_returns_true_on_success(monkeypatch: MonkeyPatch) -> None:
    parser = _new_parser()
    statuses: list[dict[str, Any]] = [
        {"status": "running"},
        {"Status": "Success"},
    ]

    def fake_query_status(task_id: str) -> dict[str, Any] | None:
        return statuses.pop(0)

    parser_any = cast(Any, parser)
    parser_any.query_status = fake_query_status
    monkeypatch.setattr("src.utils.aili_doc_parser.time.sleep", lambda _n: None)
    assert parser.wait_for_completion("t", poll_interval=0) is True


def test_submit_job_uses_models_and_client(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    parser = _new_parser()
    p = tmp_path / "a.pdf"
    p.write_bytes(b"%PDF")

    class RuntimeOptions:
        pass

    class SubmitDocParserJobAdvanceRequest:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    util_models = types.SimpleNamespace(RuntimeOptions=RuntimeOptions)
    docmind_models = types.SimpleNamespace(
        SubmitDocParserJobAdvanceRequest=SubmitDocParserJobAdvanceRequest
    )

    def fake_import_module(name: str) -> Any:
        if name == "alibabacloud_tea_util.models":
            return util_models
        if name == "alibabacloud_docmind_api20220711.models":
            return docmind_models
        raise AssertionError(name)

    monkeypatch.setattr(
        "src.utils.aili_doc_parser.importlib.import_module", fake_import_module
    )

    class FakeData:
        def __init__(self) -> None:
            self.id = "123"

    class FakeBody:
        def __init__(self) -> None:
            self.data = FakeData()

    class FakeResponse:
        def __init__(self) -> None:
            self.body = FakeBody()

    class FakeClient:
        def __init__(self) -> None:
            self.last_request: Any | None = None
            self.last_runtime: Any | None = None

        def submit_doc_parser_job_advance(self, request: Any, runtime: Any) -> Any:
            self.last_request = request
            self.last_runtime = runtime
            return FakeResponse()

    client = FakeClient()
    parser.client = client
    task_id = parser.submit_job(str(p))
    assert task_id == "123"
    assert isinstance(client.last_runtime, RuntimeOptions)
    assert client.last_request is not None
    req = cast(Any, client.last_request)
    assert req.kwargs["file_name"] == "a.pdf"
    assert req.kwargs["file_name_extension"] == "pdf"


def test_query_status_returns_to_map_dict(monkeypatch: MonkeyPatch) -> None:
    parser = _new_parser()

    class QueryDocParserStatusRequest:
        def __init__(self, *, id: str) -> None:
            self.id = id

    docmind_models = types.SimpleNamespace(
        QueryDocParserStatusRequest=QueryDocParserStatusRequest
    )

    def fake_import_module(name: str) -> Any:
        if name == "alibabacloud_docmind_api20220711.models":
            return docmind_models
        raise AssertionError(name)

    monkeypatch.setattr(
        "src.utils.aili_doc_parser.importlib.import_module", fake_import_module
    )

    class FakeData:
        def to_map(self) -> dict[str, Any]:
            return {"Status": "Success"}

    class FakeBody:
        data = FakeData()

    class FakeResponse:
        body = FakeBody()

    class FakeClient:
        def query_doc_parser_status(self, request: Any) -> Any:
            assert request.id == "tid"
            return FakeResponse()

    parser.client = FakeClient()
    assert parser.query_status("tid") == {"Status": "Success"}


def test_get_result_returns_to_map_dict(monkeypatch: MonkeyPatch) -> None:
    parser = _new_parser()

    class GetDocParserResultRequest:
        def __init__(
            self, *, id: str, layout_num: int, layout_step_size: int
        ) -> None:
            self.id = id
            self.layout_num = layout_num
            self.layout_step_size = layout_step_size

    docmind_models = types.SimpleNamespace(
        GetDocParserResultRequest=GetDocParserResultRequest
    )

    def fake_import_module(name: str) -> Any:
        if name == "alibabacloud_docmind_api20220711.models":
            return docmind_models
        raise AssertionError(name)

    monkeypatch.setattr(
        "src.utils.aili_doc_parser.importlib.import_module", fake_import_module
    )

    class FakeData:
        def to_map(self) -> dict[str, Any]:
            return {"layouts": [{"content": "x"}]}

    class FakeBody:
        data = FakeData()

    class FakeResponse:
        body = FakeBody()

    class FakeClient:
        def get_doc_parser_result(self, request: Any) -> Any:
            assert request.id == "tid"
            assert request.layout_num == 5
            assert request.layout_step_size == 10
            return FakeResponse()

    parser.client = FakeClient()
    out = parser.get_result("tid", layout_num=5, layout_step_size=10)
    assert out == {"layouts": [{"content": "x"}]}
