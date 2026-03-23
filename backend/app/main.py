from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import ensure_runtime_settings, get_settings
from app.routes import api_router
from app.utils.http import close_async_client
from app.utils.errors import VideoSparkError, as_http_exception

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app.starting")
    yield
    await close_async_client()
    logger.info("app.stopped")


def create_app() -> FastAPI:
    settings = ensure_runtime_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(VideoSparkError)
    async def handle_videospark_error(_request: Request, exc: VideoSparkError) -> JSONResponse:
        http_exc = as_http_exception(exc)
        return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
