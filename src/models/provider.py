from __future__ import annotations

from typing import Any, Protocol


class ChatModel(Protocol):
    async def ainvoke(
        self,
        input: Any,
        config: Any | None = None,
        **kwargs: Any,
    ) -> Any: ...
