from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.errors import ApiError
from app.integrations.youtube.client import (
    AuthenticatedChannel,
    AuthenticatedGoogleProfile,
    YouTubeClient,
    YouTubeUploadRequest,
)
from app.integrations.youtube.oauth import GoogleTokenBundle, OAuthStatePayload, YouTubeOAuthHelper


@dataclass
class OAuthCompletionResult:
    state_payload: OAuthStatePayload
    token_bundle: GoogleTokenBundle
    google_profile: AuthenticatedGoogleProfile
    channel: AuthenticatedChannel


class YouTubeIntegrationService:
    def __init__(self, settings: Settings, redis_client=None) -> None:
        self.settings = settings
        self.oauth = YouTubeOAuthHelper(settings, redis_client=redis_client)
        self.client = YouTubeClient(settings)

    def build_connect_url(self, *, user_id: str, workspace_id: str, redirect_path: str) -> str:
        state_payload = self.oauth.create_state(
            user_id=user_id,
            workspace_id=workspace_id,
            redirect_path=redirect_path or "/app/publishing/accounts",
        )
        authorization_url, code_verifier = self.oauth.build_authorization_url(state=state_payload.state)
        state_payload.code_verifier = code_verifier
        self.oauth.store_state(state_payload)
        return authorization_url

    def complete_callback(self, *, state: str, code: str) -> OAuthCompletionResult:
        state_payload = self.oauth.consume_state(state)
        token_bundle = self.oauth.exchange_code(
            code=code,
            state=state_payload.state,
            code_verifier=state_payload.code_verifier,
        )
        google_profile = self.client.get_google_profile(token_bundle)
        channel = self.client.get_authenticated_channel(token_bundle)
        return OAuthCompletionResult(
            state_payload=state_payload,
            token_bundle=token_bundle,
            google_profile=google_profile,
            channel=channel,
        )

    def refresh_token(self, *, refresh_token: str, scopes: list[str]) -> GoogleTokenBundle:
        return self.oauth.refresh_token(refresh_token=refresh_token, scopes=scopes)

    def token_expiring_soon(self, expiry: datetime | None) -> bool:
        if expiry is None:
            return True
        normalized = expiry if expiry.tzinfo else expiry.replace(tzinfo=UTC)
        return normalized <= datetime.now(UTC) + timedelta(minutes=5)

    def sanitize_metadata(
        self,
        *,
        title: str,
        description: str,
        tags: list[str],
    ) -> tuple[str, str, list[str]]:
        normalized_title = " ".join(title.split()).strip()
        if not normalized_title:
            raise ApiError(422, "youtube_title_required", "A YouTube title is required.")
        if len(normalized_title) > 100:
            raise ApiError(422, "youtube_title_too_long", "YouTube titles must be 100 characters or fewer.")

        normalized_description = description.strip()
        if len(normalized_description) > 5000:
            raise ApiError(
                422,
                "youtube_description_too_long",
                "YouTube descriptions must be 5000 characters or fewer.",
            )

        normalized_tags = []
        for tag in tags:
            cleaned = " ".join(tag.split()).strip()
            if cleaned:
                normalized_tags.append(cleaned[:100])
        normalized_tags = normalized_tags[:30]
        combined_tag_length = sum(len(tag) for tag in normalized_tags) + max(0, len(normalized_tags) - 1)
        if combined_tag_length > 500:
            raise ApiError(422, "youtube_tags_too_long", "Combined YouTube tags must stay under 500 characters.")
        return normalized_title, normalized_description, normalized_tags

    def prepare_upload_request(
        self,
        *,
        file_path: str,
        content_type: str,
        title: str,
        description: str,
        tags: list[str],
        visibility: str,
        publish_at: datetime | None,
    ) -> YouTubeUploadRequest:
        normalized_title, normalized_description, normalized_tags = self.sanitize_metadata(
            title=title,
            description=description,
            tags=tags,
        )
        if visibility not in {"public", "private", "unlisted"}:
            raise ApiError(422, "invalid_visibility", f"Unsupported YouTube visibility: {visibility}")
        return YouTubeUploadRequest(
            file_path=file_path,
            content_type=content_type or "video/mp4",
            title=normalized_title,
            description=normalized_description,
            tags=normalized_tags,
            visibility=visibility,
            publish_at=publish_at,
        )
