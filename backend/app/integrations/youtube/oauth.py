from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.errors import AdapterError

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
STATE_PREFIX = "youtube_oauth_state"
STATE_TTL_SECONDS = 600

logger = logging.getLogger(__name__)

GOOGLE_SCOPE_ALIASES = {
    "email": "https://www.googleapis.com/auth/userinfo.email",
    "profile": "https://www.googleapis.com/auth/userinfo.profile",
}


@dataclass
class OAuthStatePayload:
    state: str
    user_id: str
    workspace_id: str
    redirect_path: str
    code_verifier: str
    created_at: datetime


@dataclass
class GoogleTokenBundle:
    access_token: str
    refresh_token: str
    expiry: datetime | None
    scopes: list[str]
    token_type: str = "Bearer"
    id_token: str | None = None


def _require_google_oauth():
    try:
        from google.auth.transport.requests import Request
        from google.auth.exceptions import RefreshError
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise AdapterError(
            "configuration",
            "google_client_libraries_missing",
            "Google API client libraries are not installed. Run `uv sync` in backend/ to install them.",
        ) from exc
    return Flow, Credentials, Request, RefreshError


def _describe_exchange_error(exc: Exception) -> str:
    parts: list[str] = [exc.__class__.__name__]
    message = str(exc).strip()
    if message:
        parts.append(message)

    description = getattr(exc, "description", None)
    if description and str(description).strip() not in parts:
        parts.append(str(description).strip())

    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            parts.append(f"status={status_code}")
        response_text = getattr(response, "text", None)
        if response_text:
            trimmed = str(response_text).strip()
            if trimmed:
                parts.append(trimmed[:800])

    return " | ".join(parts)


class YouTubeOAuthHelper:
    def __init__(self, settings: Settings, redis_client=None) -> None:
        self.settings = settings
        self.redis = redis_client

    def scopes(self) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_scope in self.settings.youtube_scopes.split(","):
            scope = GOOGLE_SCOPE_ALIASES.get(raw_scope.strip(), raw_scope.strip())
            if scope and scope not in seen:
                normalized.append(scope)
                seen.add(scope)
        return normalized

    def _client_config(self) -> dict[str, Any]:
        if not self.settings.google_client_id or not self.settings.google_client_secret:
            raise AdapterError(
                "configuration",
                "youtube_oauth_not_configured",
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured for YouTube OAuth.",
            )
        if not self.settings.google_redirect_uri:
            raise AdapterError(
                "configuration",
                "youtube_redirect_uri_missing",
                "GOOGLE_REDIRECT_URI must point to the backend YouTube callback endpoint.",
            )
        return {
            "web": {
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "auth_uri": GOOGLE_AUTH_URI,
                "token_uri": GOOGLE_TOKEN_URI,
            }
        }

    def create_state(self, *, user_id: str, workspace_id: str, redirect_path: str) -> OAuthStatePayload:
        state = secrets.token_urlsafe(32)
        return OAuthStatePayload(
            state=state,
            user_id=user_id,
            workspace_id=workspace_id,
            redirect_path=redirect_path or "/app/publishing/accounts",
            code_verifier="",
            created_at=datetime.now(timezone.utc),
        )

    def store_state(self, payload: OAuthStatePayload) -> None:
        if self.redis is None:
            raise AdapterError(
                "configuration",
                "youtube_oauth_state_store_missing",
                "Redis is required to store YouTube OAuth state safely.",
            )
        self.redis.setex(
            f"{STATE_PREFIX}:{payload.state}",
            STATE_TTL_SECONDS,
            json.dumps(
                {
                    "state": payload.state,
                    "user_id": payload.user_id,
                    "workspace_id": payload.workspace_id,
                    "redirect_path": payload.redirect_path,
                    "code_verifier": payload.code_verifier,
                    "created_at": payload.created_at.isoformat(),
                }
            ),
        )

    def consume_state(self, state: str) -> OAuthStatePayload:
        if self.redis is None:
            raise AdapterError(
                "configuration",
                "youtube_oauth_state_store_missing",
                "Redis is required to validate the YouTube OAuth state parameter.",
            )
        key = f"{STATE_PREFIX}:{state}"
        raw = self.redis.get(key)
        if not raw:
            raise AdapterError(
                "deterministic_input",
                "youtube_oauth_state_invalid",
                "The YouTube OAuth state is missing, expired, or invalid.",
            )
        self.redis.delete(key)
        payload = json.loads(raw)
        return OAuthStatePayload(
            state=str(payload["state"]),
            user_id=str(payload["user_id"]),
            workspace_id=str(payload["workspace_id"]),
            redirect_path=str(payload.get("redirect_path") or "/app/publishing/accounts"),
            code_verifier=str(payload.get("code_verifier") or ""),
            created_at=datetime.fromisoformat(payload["created_at"]),
        )

    def build_authorization_url(self, *, state: str) -> tuple[str, str]:
        Flow, _, _, _ = _require_google_oauth()
        flow = Flow.from_client_config(
            self._client_config(),
            scopes=self.scopes(),
            redirect_uri=self.settings.google_redirect_uri,
            state=state,
        )
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        code_verifier = str(getattr(flow, "code_verifier", "") or "")
        if not code_verifier:
            raise AdapterError(
                "configuration",
                "youtube_pkce_code_verifier_missing",
                "Google OAuth flow did not generate a code verifier.",
            )
        return authorization_url, code_verifier

    def exchange_code(self, *, code: str, state: str, code_verifier: str) -> GoogleTokenBundle:
        Flow, _, _, _ = _require_google_oauth()
        flow = Flow.from_client_config(
            self._client_config(),
            scopes=self.scopes(),
            redirect_uri=self.settings.google_redirect_uri,
            state=state,
            code_verifier=code_verifier,
        )
        try:
            flow.fetch_token(code=code)
        except Exception as exc:  # pragma: no cover - upstream auth library error handling
            details = _describe_exchange_error(exc)
            logger.warning(
                "youtube_oauth_exchange_error state=%s redirect_uri=%s verifier_length=%s details=%s",
                state,
                self.settings.google_redirect_uri,
                len(code_verifier),
                details,
            )
            raise AdapterError(
                "deterministic_input",
                "youtube_oauth_exchange_failed",
                f"Google token exchange failed: {details}",
            ) from exc
        credentials = flow.credentials
        return GoogleTokenBundle(
            access_token=str(credentials.token or ""),
            refresh_token=str(credentials.refresh_token or ""),
            expiry=credentials.expiry,
            scopes=list(credentials.scopes or self.scopes()),
            token_type=str(getattr(credentials, "token_type", "Bearer") or "Bearer"),
            id_token=(credentials.id_token if hasattr(credentials, "id_token") else None),
        )

    def refresh_token(self, *, refresh_token: str, scopes: list[str] | None = None) -> GoogleTokenBundle:
        _, Credentials, Request, RefreshError = _require_google_oauth()
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
            scopes=scopes or self.scopes(),
        )
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise AdapterError(
                "deterministic_input",
                "youtube_refresh_failed",
                "Google rejected the stored YouTube refresh token.",
            ) from exc
        except Exception as exc:  # pragma: no cover - upstream auth library error handling
            raise AdapterError(
                "transient",
                "youtube_refresh_unavailable",
                "Refreshing the YouTube access token failed temporarily.",
            ) from exc
        return GoogleTokenBundle(
            access_token=str(credentials.token or ""),
            refresh_token=str(credentials.refresh_token or refresh_token),
            expiry=credentials.expiry,
            scopes=list(credentials.scopes or scopes or self.scopes()),
            token_type=str(getattr(credentials, "token_type", "Bearer") or "Bearer"),
        )
