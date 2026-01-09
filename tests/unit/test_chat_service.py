from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.agent.chat_handler import ChatService
from src.models.entities import Message


@dataclass
class _Result:
    content: str


class _FakeModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[object] = []

    async def ainvoke(
        self,
        input: object,
        config: object | None = None,
        **kwargs: object,
    ) -> _Result:
        self.calls.append(input)
        return _Result(content=self.reply)


def test_chat_service_reply_returns_model_content() -> None:
    model = _FakeModel(reply="hello")
    service = ChatService(model=model, system_prompt="sys")

    history = [Message(role="user", content="hi"), Message(role="assistant", content="ok")]
    out = asyncio.run(service.reply(language="zh", history=history))

    assert out == "hello"
    assert len(model.calls) == 1
