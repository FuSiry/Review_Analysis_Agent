from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from _pytest.monkeypatch import MonkeyPatch
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.models.chat_model import ToolCallingChatModel


@dataclass
class _Tool:
    name: str
    calls: list[dict[str, Any]]

    async def ainvoke(self, input: dict[str, Any]) -> str:
        self.calls.append(input)
        return "ok"


class _BaseModel:
    def __init__(self) -> None:
        self.calls: list[list[object]] = []
        self._bound_tools: list[Any] = []

    def bind_tools(self, tools: list[Any]) -> _BaseModel:
        self._bound_tools = tools
        return self

    async def ainvoke(
        self,
        input: Any,
        config: Any | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        if isinstance(input, list):
            self.calls.append(input)
            has_tool_msg = any(getattr(m, "type", None) == "tool" for m in input)
            if has_tool_msg:
                return AIMessage(content="done")
        return AIMessage(
            content="",
            tool_calls=[{"id": "c1", "name": "t1", "args": {"q": "x"}}],
        )


def test_tool_calling_model_executes_tools(monkeypatch: MonkeyPatch) -> None:
    tool = _Tool(name="t1", calls=[])
    monkeypatch.setattr("src.models.chat_model.load_mcp_tools", lambda: asyncio.sleep(0, [tool]))

    model = ToolCallingChatModel(_BaseModel())
    out = asyncio.run(
        model.ainvoke([SystemMessage(content="s"), HumanMessage(content="h")])
    )
    assert getattr(out, "content", None) == "done"
    assert tool.calls == [{"q": "x"}]


def test_tool_calling_model_no_tools_delegates(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("src.models.chat_model.load_mcp_tools", lambda: asyncio.sleep(0, []))
    base = _BaseModel()
    model = ToolCallingChatModel(base)
    out = asyncio.run(
        model.ainvoke([SystemMessage(content="s"), HumanMessage(content="h")])
    )
    assert getattr(out, "tool_calls", None)
    assert len(base.calls) == 1
