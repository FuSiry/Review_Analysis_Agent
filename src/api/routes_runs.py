from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.agent.review_handler import ReviewService
from src.api.deps import (
    get_document_parser,
    get_file_store,
    get_review_service,
    get_run_store,
    get_session_store,
)
from src.api.run_store import InMemoryRunStore
from src.api.session_store import InMemorySessionStore
from src.models.enums import Mode
from src.models.events import EventType, RunEvent
from src.models.run import Run, RunPhase, RunStatus
from src.utils.document_parser import DocumentParser
from src.utils.file_store import FileStore

router = APIRouter(prefix="/api")


class CancelRunResponse(BaseModel):
    run_id: str
    status: RunStatus


class StartReviewBody(BaseModel):
    session_id: str
    document_id: str | None = None
    text: str | None = None
    filename: str | None = None


class StartReviewResponse(BaseModel):
    run_id: str


@router.get("/runs/{run_id}", response_model=Run)
async def get_run(run_id: str, store: InMemoryRunStore = Depends(get_run_store)) -> Run:
    """Get run detail.

    Args:
        run_id: Run identifier.

    Returns:
        Run detail.
    """

    item = store.get(run_id)
    if not item:
        raise HTTPException(status_code=404, detail="run not found")
    return item.run


@router.post("/reviews", response_model=StartReviewResponse)
async def start_review(
    body: StartReviewBody,
    sessions: InMemorySessionStore = Depends(get_session_store),
    store: InMemoryRunStore = Depends(get_run_store),
    file_store: FileStore = Depends(get_file_store),
    parser: DocumentParser = Depends(get_document_parser),
    service: ReviewService = Depends(get_review_service),
) -> StartReviewResponse:
    """Start a review run.

    Args:
        body: Review request.

    Returns:
        Run metadata.
    """

    session = sessions.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if session.mode == Mode.chat:
        raise HTTPException(status_code=400, detail="chat mode does not support review")

    run = store.create(session_id=session.id, mode=session.mode, document_id=body.document_id)
    store.set_phase(run.id, RunPhase.received)
    store.add_event(RunEvent(run_id=run.id, type=EventType.info, message="received"))

    async def emit(event_type: EventType, message: str) -> None:
        store.add_event(RunEvent(run_id=run.id, type=event_type, message=message))

    def should_cancel() -> bool:
        item = store.get(run.id)
        return bool(item and item.run.status == RunStatus.canceled)

    async def worker() -> None:
        try:
            text = (body.text or "").strip()
            if not text:
                if not body.document_id:
                    raise ValueError("document_id or text is required")
                manifest = file_store.get_manifest("document", body.document_id)
                if not manifest:
                    raise ValueError("document not found")
                store.set_phase(run.id, RunPhase.parsing)
                await emit(EventType.info, "parsing")
                from pathlib import Path

                text = await parser.parse(Path(manifest.path))
            store.set_phase(run.id, RunPhase.planning)
            result = await service.review(
                mode=session.mode,
                language=session.language,
                document=text,
                emit=emit,
                should_cancel=should_cancel,
            )
            if should_cancel():
                store.set_status(run.id, RunStatus.canceled)
                await emit(EventType.info, "canceled")
                return
            store.set_phase(run.id, RunPhase.producing)
            filename = body.filename or f"{session.mode.value}.md"
            artifact = file_store.save_review(
                result,
                filename,
                session_id=session.id,
                run_id=run.id,
                source_document_id=body.document_id,
            )
            store.set_artifact(run.id, artifact.manifest.id)
            store.set_status(run.id, RunStatus.succeeded)
            await emit(EventType.info, "succeeded")
        except Exception as e:
            if should_cancel() or str(e) == "canceled":
                store.set_status(run.id, RunStatus.canceled)
                await emit(EventType.info, "canceled")
                return
            store.set_status(run.id, RunStatus.failed, error=str(e))
            await emit(EventType.error, str(e))

    asyncio.create_task(worker())
    return StartReviewResponse(run_id=run.id)


@router.post("/runs/{run_id}/cancel", response_model=CancelRunResponse)
async def cancel_run(
    run_id: str,
    store: InMemoryRunStore = Depends(get_run_store),
) -> CancelRunResponse:
    """Cancel an ongoing run.

    Args:
        run_id: Run identifier.

    Returns:
        Cancel result.
    """

    item = store.get(run_id)
    if not item:
        raise HTTPException(status_code=404, detail="run not found")
    store.set_status(run_id, RunStatus.canceled)
    store.add_event(RunEvent(run_id=run_id, type=EventType.info, message="canceled"))
    updated = store.get(run_id)
    if not updated:
        raise HTTPException(status_code=404, detail="run not found")
    return CancelRunResponse(run_id=updated.run.id, status=updated.run.status)


@router.get("/runs/{run_id}/events", response_model=list[RunEvent])
async def get_events(
    run_id: str,
    store: InMemoryRunStore = Depends(get_run_store),
) -> list[RunEvent]:
    """Get run events.

    Args:
        run_id: Run identifier.

    Returns:
        Run events.
    """

    item = store.get(run_id)
    if not item:
        raise HTTPException(status_code=404, detail="run not found")
    return item.events
