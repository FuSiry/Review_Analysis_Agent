from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.models.enums import Mode
from src.models.events import RunEvent
from src.models.run import Run, RunPhase, RunStatus


@dataclass
class RunWithEvents:
    run: Run
    events: list[RunEvent]


class InMemoryRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunWithEvents] = {}

    def create(self, session_id: str, mode: Mode, document_id: str | None = None) -> Run:
        run_id = uuid.uuid4().hex
        run = Run(id=run_id, session_id=session_id, mode=mode, document_id=document_id)
        self._runs[run_id] = RunWithEvents(run=run, events=[])
        return run

    def get(self, run_id: str) -> RunWithEvents | None:
        return self._runs.get(run_id)

    def set_phase(self, run_id: str, phase: RunPhase) -> None:
        item = self._runs[run_id]
        item.run.phase = phase

    def set_status(self, run_id: str, status: RunStatus, error: str | None = None) -> None:
        item = self._runs[run_id]
        item.run.status = status
        item.run.error = error

    def set_artifact(self, run_id: str, artifact_id: str) -> None:
        item = self._runs[run_id]
        item.run.artifact_id = artifact_id

    def add_event(self, event: RunEvent) -> None:
        item = self._runs[event.run_id]
        item.events.append(event)
