from __future__ import annotations

import os

from fastapi import FastAPI

from src.api.error_handlers import install_error_handlers
from src.api.routes_artifacts import router as artifacts_router
from src.api.routes_documents import router as documents_router
from src.api.routes_runs import router as runs_router
from src.api.routes_sessions import router as sessions_router


class _SolaraContextResetApp:
    def __init__(self, app) -> None:
        self._app = app

    async def __call__(self, scope, receive, send) -> None:
        from solara.server import kernel_context

        with kernel_context.without_context():
            await self._app(scope, receive, send)


def create_app() -> FastAPI:
    os.environ.setdefault("DOCMIND_ENABLED", "1")
    app = FastAPI(
        title="Review Analysis Agent",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)
    app.include_router(sessions_router)
    app.include_router(documents_router)
    app.include_router(artifacts_router)
    app.include_router(runs_router)
    os.environ["SOLARA_APP"] = "src.cli.app:Page"
    from solara.server.starlette import app as solara_app

    app.mount("/", _SolaraContextResetApp(solara_app))
    return app


app = create_app()
