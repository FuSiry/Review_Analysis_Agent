from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatModelSettings(BaseModel):
    model: str
    api_key: str | None = None
    type: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ModelsConfig(BaseModel):
    chat_model: ChatModelSettings


class AppConfig(BaseModel):
    models: ModelsConfig

