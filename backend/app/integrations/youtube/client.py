from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.core.config import Settings
from app.core.errors import AdapterError
from app.integrations.youtube.oauth import GOOGLE_TOKEN_URI, GoogleTokenBundle

UTC = timezone.utc


@dataclass
class AuthenticatedGoogleProfile:
    email: str | None
    subject: str | None


@dataclass
class AuthenticatedChannel:
    channel_id: str
    title: str
    handle: str | None


@dataclass
class YouTubeUploadRequest:
    file_path: str
    content_type: str
    title: str
    description: str
    tags: list[str]
    visibility: str
    publish_at: datetime | None = None


@dataclass
class YouTubeUploadResult:
    youtube_video_id: str
    video_url: str
    raw_response: dict[str, object]


def _require_google_client():
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise AdapterError(
            "configuration",
            "google_client_libraries_missing",
            "Google API client libraries are not installed. Run `uv sync` in backend/ to install them.",
        ) from exc
    return Credentials, build, HttpError, MediaFileUpload


def _normalized_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _http_error_to_adapter(exc, *, fallback_code: str) -> AdapterError:
    status_code = getattr(getattr(exc, "resp", None), "status", None) or 500
    content = getattr(exc, "content", b"")
    if isinstance(content, bytes):
        content_text = content.decode("utf-8", errors="ignore")
    else:
        content_text = str(content)
    lowered = content_text.lower()

    if status_code in {500, 502, 503, 504}:
        return AdapterError("transient", fallback_code, "YouTube is temporarily unavailable.")
    if status_code == 401:
        return AdapterError("transient", "youtube_unauthorized", "The YouTube access token is no longer valid.")
    if status_code == 403 and any(
        marker in lowered
        for marker in ("backenderror", "quotaexceeded", "ratelimitexceeded", "userratelimitexceeded")
    ):
        return AdapterError("transient", "youtube_quota_or_rate_limited", "YouTube rejected the request temporarily.")
    if status_code in {400, 403, 404, 409, 422}:
        return AdapterError(
            "deterministic_input",
            "youtube_invalid_request",
            content_text[:800] or "YouTube rejected the request payload.",
        )
    return AdapterError("transient", fallback_code, content_text[:800] or "A YouTube API call failed.")


class YouTubeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _credentials(self, token_bundle: GoogleTokenBundle):
        Credentials, _, _, _ = _require_google_client()
        return Credentials(
            token=token_bundle.access_token,
            refresh_token=token_bundle.refresh_token,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
            scopes=token_bundle.scopes,
        )

    def get_google_profile(self, token_bundle: GoogleTokenBundle) -> AuthenticatedGoogleProfile:
        _, build, HttpError, _ = _require_google_client()
        try:
            oauth2 = build("oauth2", "v2", credentials=self._credentials(token_bundle), cache_discovery=False)
            payload = oauth2.userinfo().get().execute()
        except HttpError as exc:
            raise _http_error_to_adapter(exc, fallback_code="youtube_google_profile_failed") from exc
        return AuthenticatedGoogleProfile(
            email=payload.get("email"),
            subject=payload.get("id"),
        )

    def get_authenticated_channel(self, token_bundle: GoogleTokenBundle) -> AuthenticatedChannel:
        _, build, HttpError, _ = _require_google_client()
        try:
            youtube = build("youtube", "v3", credentials=self._credentials(token_bundle), cache_discovery=False)
            payload = youtube.channels().list(part="snippet", mine=True).execute()
        except HttpError as exc:
            raise _http_error_to_adapter(exc, fallback_code="youtube_channel_lookup_failed") from exc
        items = payload.get("items") or []
        if not items:
            raise AdapterError(
                "deterministic_input",
                "youtube_channel_not_found",
                "No YouTube channel was returned for the authenticated Google account.",
            )
        channel = items[0]
        snippet = channel.get("snippet") or {}
        handle = snippet.get("customUrl")
        return AuthenticatedChannel(
            channel_id=str(channel.get("id") or ""),
            title=str(snippet.get("title") or "Untitled channel"),
            handle=(str(handle).strip() if handle else None),
        )

    def upload_video(
        self,
        token_bundle: GoogleTokenBundle,
        payload: YouTubeUploadRequest,
        *,
        progress_callback: Callable[[int], None] | None = None,
    ) -> YouTubeUploadResult:
        _, build, HttpError, MediaFileUpload = _require_google_client()
        youtube = build("youtube", "v3", credentials=self._credentials(token_bundle), cache_discovery=False)
        media = MediaFileUpload(
            Path(payload.file_path).as_posix(),
            mimetype=payload.content_type or "video/mp4",
            resumable=True,
            chunksize=8 * 1024 * 1024,
        )

        status_payload: dict[str, object] = {
            "privacyStatus": "private" if payload.publish_at else payload.visibility,
        }
        publish_at = _normalized_utc(payload.publish_at)
        if publish_at is not None:
            status_payload["publishAt"] = publish_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": payload.title,
                    "description": payload.description,
                    "tags": payload.tags,
                },
                "status": status_payload,
            },
            media_body=media,
        )
        response = None
        try:
            while response is None:
                status, response = request.next_chunk(num_retries=0)
                if status is not None and progress_callback is not None:
                    progress_callback(max(1, min(99, int(status.progress() * 100))))
        except HttpError as exc:
            raise _http_error_to_adapter(exc, fallback_code="youtube_upload_failed") from exc
        except Exception as exc:  # pragma: no cover - defensive guard around resumable upload loop
            raise AdapterError("transient", "youtube_upload_interrupted", str(exc)) from exc

        if progress_callback is not None:
            progress_callback(100)
        youtube_video_id = str(response.get("id") or "")
        if not youtube_video_id:
            raise AdapterError("transient", "youtube_missing_video_id", "YouTube did not return a video ID.")
        return YouTubeUploadResult(
            youtube_video_id=youtube_video_id,
            video_url=f"https://www.youtube.com/watch?v={youtube_video_id}",
            raw_response=json.loads(json.dumps(response)),
        )
