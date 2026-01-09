from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.models.entities import Message, Session
from src.models.enums import Mode


@dataclass
class CreateSessionRequest:
    mode: Mode
    language: str


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(self, mode: Mode, language: str) -> Session:
        session_id = uuid.uuid4().hex
        session = Session(id=session_id, mode=mode, language=language)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def append_message(self, session_id: str, message: Message) -> Session:
        session = self._sessions[session_id]
        session.messages.append(message)
        self._sessions[session_id] = session
        return session

