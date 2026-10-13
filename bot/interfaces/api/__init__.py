"""QA Bot v0.2 FastAPI app — router-based, mirroring the root project's structure.

Self-contained: imports only from `bot`. Aggregates one router per phase under
the `/api/v2` prefix, adds a correlation-id header, and a unified error envelope.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from bot import __version__
from bot.interfaces.api.routers.artifacts import router as artifacts_router
from bot.interfaces.api.routers.crawl import router as crawl_router
from bot.interfaces.api.routers.execute import router as execute_router
from bot.interfaces.api.routers.ground import router as ground_router
from bot.interfaces.api.routers.health import router as health_router
from bot.interfaces.api.routers.plan import router as plan_router
from bot.interfaces.api.routers.report import router as report_router
from bot.interfaces.api.routers.verify import router as verify_router
from bot.interfaces.api.schemas import ErrorEnvelope
from bot.settings import get_settings

logger = logging.getLogger("qa_bot.api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="QA Bot v0.2 API",
        description="Standalone autonomous QA pipeline — Phases 1-6.",
        version=__version__,
        docs_url="/api/v2/docs",
        openapi_url="/api/v2/openapi.json",
        redoc_url="/api/v2/redoc",
    )
    prefix = settings.API_V2_PREFIX

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        run_id = request.headers.get("X-Run-Id") or secrets.token_hex(8)
        request.state.run_id = run_id
        response = await call_next(request)
        response.headers["X-Run-Id"] = run_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        run_id = getattr(request.state, "run_id", None)
        envelope = ErrorEnvelope(
            error={"code": str(exc.status_code), "message": str(exc.detail)}, run_id=run_id)
        return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())

    for r in (health_router, crawl_router, ground_router, plan_router,
              execute_router, verify_router, report_router, artifacts_router):
        app.include_router(r, prefix=prefix)

    return app


app = create_app()

