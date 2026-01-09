from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.models.enums import Mode


class RunStatus(StrEnum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class RunPhase(StrEnum):
    received = "received"
    parsing = "parsing"
    planning = "planning"
    executing = "executing"
    producing = "producing"


class Run(BaseModel):
    id: str
    session_id: str
    mode: Mode
    status: RunStatus = RunStatus.running
    phase: RunPhase = RunPhase.received
    created_at: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None
    document_id: str | None = None
    artifact_id: str | None = None
