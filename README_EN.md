**其他语言版本: [中文](README.md), [English](README_EN.md).**

# Review Analysis Agent

## What It Does

Review Analysis Agent is a single-process web app (UI + API in one server) for:

- `chat`: multi-turn chatting with an LLM
- `prd_review`: PRD (Product Requirements Doc) review
- `trd_review`: TRD (Technical Requirements/Design Doc) review
- `tc_review`: Test case document review

In review modes, users can paste text or upload a document. Uploaded documents and generated review artifacts are stored locally with a 1-day TTL.

## Architecture

- Solara UI: `src/cli/app.py`
- FastAPI REST API: `src/api/routes_*.py`
- Plan-and-Execute review logic: `src/agent/review_handler.py`
- Document parsing: `src/utils/document_parser.py` (DocMind for PDFs/Office; plain read for md/txt)
- TTL file storage: `src/utils/file_store.py` (documents/reviews + manifests)

## Installation

Dependencies are managed via `pyproject.toml`. Recommended: uv.

```bash
uv sync --all-extras
```

## Configuration

LLM settings are in `src/config.yaml`:

- `models.chat_model.base_url`
- `models.chat_model.api_key`
- `models.chat_model.model`

DocMind parsing is enabled by default (`DOCMIND_ENABLED=1`). To disable DocMind:

```bash
export DOCMIND_ENABLED=0
```

When `DOCMIND_ENABLED=1` and a non-`.md/.txt` document is uploaded, the server calls Alibaba Cloud DocMind SDK (requires Alibaba Cloud credentials in your environment).

## Run

Start the dev server (UI + API):

```bash
uv run uvicorn src.cli.server:app --host 127.0.0.1 --port 8000
or python3 -m src.main
```

- UI: `http://127.0.0.1:8000/`
- OpenAPI: `http://127.0.0.1:8000/api/docs`


## Dev Commands

```bash
uv run ruff check .
uv run mypy .
uv run pytest
```

