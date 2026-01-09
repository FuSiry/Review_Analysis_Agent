from __future__ import annotations

from datetime import timedelta

from src.agent.chat_handler import ChatService
from src.agent.review_handler import ReviewService
from src.api.run_store import InMemoryRunStore
from src.api.session_store import InMemorySessionStore
from src.config.loader import load_config
from src.config.schema import AppConfig
from src.models.chat_model import init_chat_model
from src.models.enums import Mode
from src.models.run import RunStatus
from src.prompt.registry import get_prompt_text
from src.utils.document_parser import DocumentParser
from src.utils.file_store import FileStore
from src.utils.storage_paths import get_datas_dir

_sessions = InMemorySessionStore()
_runs = InMemoryRunStore()
_document_parser = DocumentParser()


def get_config() -> AppConfig:
    return load_config()


def get_session_store() -> InMemorySessionStore:
    return _sessions


def get_file_store() -> FileStore:
    return FileStore(base_dir=get_datas_dir(), ttl=timedelta(days=1))


def get_chat_service() -> ChatService:
    model = init_chat_model()
    system_prompt = get_prompt_text(Mode.chat)
    return ChatService(model=model, system_prompt=system_prompt)


def get_run_store() -> InMemoryRunStore:
    return _runs


def get_document_parser() -> DocumentParser:
    return _document_parser


def get_review_service() -> ReviewService:
    model = init_chat_model()
    return ReviewService(model=model)


def get_run_status_succeeded() -> RunStatus:
    return RunStatus.succeeded


def get_run_status_canceled() -> RunStatus:
    return RunStatus.canceled
