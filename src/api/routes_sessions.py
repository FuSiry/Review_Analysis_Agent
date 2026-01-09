from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.agent.chat_handler import ChatService
from src.api.deps import get_chat_service, get_session_store
from src.api.session_store import InMemorySessionStore
from src.models.entities import Message, Session
from src.models.enums import Mode

router = APIRouter(prefix="/api")


class CreateSessionBody(BaseModel):
    mode: Mode
    language: str


class CreateMessageBody(BaseModel):
    content: str


@router.post("/sessions", response_model=Session)
async def create_session(
    body: CreateSessionBody,
    store: InMemorySessionStore = Depends(get_session_store),
) -> Session:
    """Create a new session.

    Args:
        body: Session creation payload.

    Returns:
        The created session.
    """

    return store.create_session(mode=body.mode, language=body.language)


@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    store: InMemorySessionStore = Depends(get_session_store),
) -> Session:
    """Get session detail.

    Args:
        session_id: Session identifier.

    Returns:
        Session detail.
    """

    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.post("/sessions/{session_id}/messages", response_model=Session)
async def post_message(
    session_id: str,
    body: CreateMessageBody,
    store: InMemorySessionStore = Depends(get_session_store),
    chat_service: ChatService = Depends(get_chat_service),
) -> Session:
    """Append a user message.

    Args:
        session_id: Session identifier.
        body: Message payload.

    Returns:
        Updated session.
    """

    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    store.append_message(session_id, Message(role="user", content=body.content))

    updated = store.get_session(session_id)
    if not updated:
        raise HTTPException(status_code=404, detail="session not found")

    if updated.mode == Mode.chat:
        assistant = await chat_service.reply(updated.language, updated.messages)
        store.append_message(session_id, Message(role="assistant", content=assistant))
    else:
        store.append_message(session_id, Message(role="assistant", content=""))

    updated = store.get_session(session_id)
    if not updated:
        raise HTTPException(status_code=404, detail="session not found")
    return updated
