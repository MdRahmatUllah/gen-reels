from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.jwt import decode_token


@dataclass(frozen=True)
class RateLimitRule:
    scope: str
    limit: int
    window_seconds: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    AUTH_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/password-reset/request",
        "/api/v1/auth/password-reset/confirm",
    }

    def _resolve_rule(self, request: Request) -> RateLimitRule | None:
        path = request.url.path
        method = request.method.upper()
        if path in self.AUTH_PATHS:
            return RateLimitRule(scope="auth", limit=20, window_seconds=60)
        if method == "POST" and path.endswith(":generate"):
            return RateLimitRule(scope="generation", limit=10, window_seconds=60)
        if method in {"POST", "PATCH", "DELETE"} and path.startswith("/api/v1/"):
            return RateLimitRule(scope="write", limit=60, window_seconds=60)
        return None

    def _subject_key(self, request: Request, scope: str) -> str:
        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        if scope == "auth":
            return f"ip:{client_ip}"

        token = request.cookies.get(settings.access_cookie_name)
        if token:
            try:
                payload = decode_token(token, settings.jwt_public_key_resolved, expected_type="access")
                return f"workspace:{payload['workspace_id']}:user:{payload['sub']}"
            except Exception:
                return f"ip:{client_ip}"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next):
        rule = self._resolve_rule(request)
        if rule is None or not hasattr(request.app.state, "redis"):
            return await call_next(request)

        client = request.app.state.redis
        subject = self._subject_key(request, rule.scope)
        key = f"rate_limit:{rule.scope}:{request.method}:{request.url.path}:{subject}"
        count = client.incr(key)
        if count == 1:
            client.expire(key, rule.window_seconds)

        if count > rule.limit:
            correlation_id = getattr(request.state, "correlation_id", None)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Rate limit exceeded. Please retry later.",
                        "correlation_id": correlation_id,
                    }
                },
            )

        return await call_next(request)
