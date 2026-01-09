from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from src.agent.review_handler import ReviewService
from src.models.enums import Mode
from src.models.events import EventType


@dataclass
class _Result:
    content: str


class _FakeModel:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls: list[object] = []

    async def ainvoke(
        self,
        input: object,
        config: object | None = None,
        **kwargs: object,
    ) -> _Result:
        self.calls.append(input)
        idx = len(self.calls) - 1
        return _Result(content=self._responses[idx])


def test_review_service_happy_path_emits_events_and_returns_final() -> None:
    model = _FakeModel(
        responses=[
            "[{\"id\": \"T1\", \"title\": \"t1\"}, {\"id\": \"T2\", \"title\": \"t2\"}]",
            "{\"covered\": [\"T1\"], \"markdown\": \"p1\"}",
            "{\"covered\": [\"T2\"], \"markdown\": \"p2\"}",
            "final",
        ]
    )
    service = ReviewService(model=model, max_chars_per_chunk=3)

    events: list[tuple[EventType, str]] = []

    async def emit(event_type: EventType, message: str) -> None:
        events.append((event_type, message))

    result = asyncio.run(
        service.review(
            mode=Mode.prd_review,
            language="zh",
            document="abcdef",
            emit=emit,
            should_cancel=lambda: False,
        )
    )

    assert result == "final"
    assert (EventType.info, "planning") in events
    todo_messages = [m for t, m in events if t == EventType.todo]
    assert any(m.startswith("[pending] T1") for m in todo_messages)
    assert any(m.startswith("[pending] T2") for m in todo_messages)
    assert any(m.startswith("[done] T1") for m in todo_messages)
    assert any(m.startswith("[done] T2") for m in todo_messages)
    assert any(t == EventType.info and m.startswith("executing") for t, m in events)
    assert (EventType.info, "producing") in events
    assert len(model.calls) == 4


def test_review_service_cancellation_raises() -> None:
    model = _FakeModel(responses=["[\"t1\"]"])
    service = ReviewService(model=model, max_chars_per_chunk=10)

    with pytest.raises(ValueError, match="canceled"):
        asyncio.run(
            service.review(
                mode=Mode.trd_review,
                language="zh",
                document="abc",
                should_cancel=lambda: True,
            )
        )


def test_review_service_plan_fallback_parses_lines() -> None:
    model = _FakeModel(responses=["- a\n- b\n", "{\"covered\": [], \"markdown\": \"p\"}", "final"])
    service = ReviewService(model=model, max_chars_per_chunk=10)

    result = asyncio.run(
        service.review(
            mode=Mode.tc_review,
            language="zh",
            document="abc",
            should_cancel=lambda: False,
        )
    )

    assert result == "final"
