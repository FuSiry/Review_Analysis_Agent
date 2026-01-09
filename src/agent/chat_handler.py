from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.models.entities import Message
from src.models.provider import ChatModel


@dataclass(frozen=True)
class ChatService:
    model: ChatModel
    system_prompt: str

    async def reply(self, language: str, history: list[Message]) -> str:
        messages: list[Any] = [
            SystemMessage(content=f"{self.system_prompt}\n\nLanguage: {language}"),
        ]
        for m in history:
            if m.role == "user":
                messages.append(HumanMessage(content=m.content))
            else:
                messages.append(AIMessage(content=m.content))

        result = await self.model.ainvoke(messages)
        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content
        return str(result)

