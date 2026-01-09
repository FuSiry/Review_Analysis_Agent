from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.models.enums import Mode


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    id: str
    mode: Mode
    language: str
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    id: str
    filename: str
    content_type: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class Artifact(BaseModel):
    id: str
    filename: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

