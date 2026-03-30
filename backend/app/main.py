from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis
import uvicorn
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.jwt import decode_token
from app.core.logging import CorrelationIdMiddleware, configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import get_engine, get_session_factory
from app.integrations.storage import build_storage_client
from app.services.billing_service import BillingService

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
    settings.app_encryption_key_resolved
    configure_logging()
    app.state.settings = settings
    app.state.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.storage = build_storage_client(settings)
    get_engine(settings.database_url)
    logger.info("app_startup_complete")
    yield
    app.state.redis.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Reels Generation Backend", version="0.1.0", lifespan=lifespan)
    allowed_origins = {settings.frontend_base_url.rstrip("/")}
    if settings.frontend_base_url.startswith("http://localhost:"):
        allowed_origins.add(settings.frontend_base_url.replace("localhost", "127.0.0.1", 1).rstrip("/"))
    if settings.frontend_base_url.startswith("http://127.0.0.1:"):
        allowed_origins.add(settings.frontend_base_url.replace("127.0.0.1", "localhost", 1).rstrip("/"))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Quota-Credits-Remaining", "X-Quota-Credits-Total"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.middleware("http")
    async def quota_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        settings = request.app.state.settings
        token = request.cookies.get(settings.access_cookie_name)
        if not token:
            return response
        try:
            payload = decode_token(token, settings.jwt_public_key_resolved, expected_type="access")
            workspace_id = payload.get("workspace_id")
            if not workspace_id:
                return response
            session = get_session_factory(settings.database_url)()
            try:
                headers = BillingService(session, settings).quota_headers_for_workspace(workspace_id)
            finally:
                session.close()
            for name, value in headers.items():
                response.headers[name] = value
        except Exception:
            return response
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        payload = _error_payload(exc.message, exc.code, correlation_id)
        if exc.details is not None:
            payload["details"] = exc.details
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(payload),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder({
                **_error_payload("Request validation failed.", "validation_error", correlation_id),
                "details": exc.errors(),
            }),
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
