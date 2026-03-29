from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.logging import CorrelationIdMiddleware, configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import get_engine
from app.integrations.storage import build_storage_client

logger = logging.getLogger(__name__)


def _error_payload(message: str, code: str, correlation_id: str | None) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
        }
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging()
    app.state.settings = settings
    app.state.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.storage = build_storage_client(settings)
    get_engine(settings.database_url)
    logger.info("app_startup_complete")
    yield
    app.state.redis.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Reels Generation Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.include_router(api_router, prefix=get_settings().api_v1_prefix)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        payload = _error_payload(exc.message, exc.code, correlation_id)
        if exc.details is not None:
            payload["details"] = exc.details
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=422,
            content={
                **_error_payload("Request validation failed.", "validation_error", correlation_id),
                "details": exc.errors(),
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz(request: Request) -> dict[str, object]:
        settings = request.app.state.settings
        with get_engine(settings.database_url).connect() as connection:
            connection.execute(text("SELECT 1"))
        request.app.state.redis.ping()
        request.app.state.storage.healthcheck()
        return {"status": "ok", "checks": {"database": "ok", "redis": "ok", "storage": "ok"}}

    return app


app = create_app()


def run() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
