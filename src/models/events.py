from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    info = "info"
    todo = "todo"
    error = "error"


class RunEvent(BaseModel):
    run_id: str
    type: EventType
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

