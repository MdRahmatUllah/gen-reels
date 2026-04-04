from __future__ import annotations

import mimetypes
import tempfile
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import AdapterError, ApiError
from app.integrations.ffmpeg import FFmpegError, FFmpegRunner
from app.integrations.media_ops import probe_media_bytes
from app.integrations.storage import StorageClient, build_storage_client
from app.integrations.youtube.service import YouTubeIntegrationService
from app.integrations.captions import transcribe_audio_bytes
from app.models.youtube import (
    Video,
    VideoLifecycleStatus,
    VideoMetadataSource,
    VideoMetadataVersion,
    VideoTranscript,
)
from app.services.audit_service import record_structured_audit_log
from app.services.publishing_presenters import video_to_dict
from app.services.routing_service import RoutingService
from app.services.youtube_account_service import YouTubeAccountService

VIDEO_UPLOAD_BUCKET = "reels-publishing-videos"
SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
}


class VideoService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._storage: StorageClient | None = None
        self.youtube_integration = YouTubeIntegrationService(settings)

    @property
    def storage(self) -> StorageClient:
        if self._storage is None:
            self._storage = build_storage_client(self.settings)
        return self._storage

    def list_videos(self, auth: AuthContext) -> list[dict[str, object]]:
        videos = self.db.scalars(
            select(Video)
            .where(
                Video.workspace_id == uuid.UUID(auth.workspace_id),
                Video.owner_user_id == uuid.UUID(auth.user_id),
                Video.deleted_at.is_(None),
            )
            .order_by(Video.created_at.desc())
        ).all()
        return self._serialize_videos(videos)

    def get_video(self, auth: AuthContext, video_id: str) -> dict[str, object]:
        video = self._get_owned_video(auth, video_id)
        return self._serialize_videos([video])[0]

    def upload_video(
        self,
        auth: AuthContext,
        *,
        file_name: str,
        content_type: str | None,
        bytes_payload: bytes,
    ) -> dict[str, object]:
        safe_name = Path(file_name or "upload.mp4").name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
            raise ApiError(422, "unsupported_video_type", f"Unsupported video extension: {suffix or 'unknown'}")
        if not bytes_payload:
            raise ApiError(422, "empty_video_upload", "Uploaded video file is empty.")

        workspace_id = uuid.UUID(auth.workspace_id)
        owner_user_id = uuid.UUID(auth.user_id)
        inferred_content_type = content_type or mimetypes.guess_type(safe_name)[0] or "video/mp4"
        record_structured_audit_log(
            self.db,
            workspace_id=workspace_id,
            user_id=owner_user_id,
            action="video_upload_started",
            target_type="video_upload",
            target_id=None,
            payload={"original_file_name": safe_name, "content_type": inferred_content_type},
        )
        self.db.commit()

        video_id = uuid.uuid4()
        object_name = f"{auth.workspace_id}/{video_id}/{safe_name}"
        try:
            probe = probe_media_bytes(
                self.settings,
                file_name=safe_name,
                bytes_payload=bytes_payload,
            )
            video_stream = next(
                (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
                {},
            )
            duration_ms = None
            raw_duration = probe.get("format", {}).get("duration")
            if raw_duration:
                duration_ms = int(float(raw_duration) * 1000) or None

            self.storage.put_bytes(
                VIDEO_UPLOAD_BUCKET,
                object_name,
                bytes_payload,
                content_type=inferred_content_type,
            )

            video = Video(
                id=video_id,
                workspace_id=workspace_id,
                owner_user_id=owner_user_id,
                original_file_name=safe_name,
                storage_bucket=VIDEO_UPLOAD_BUCKET,
                storage_object_name=object_name,
                content_type=inferred_content_type,
                size_bytes=len(bytes_payload),
                duration_ms=duration_ms,
                width=int(video_stream.get("width") or 0) or None,
                height=int(video_stream.get("height") or 0) or None,
                status=VideoLifecycleStatus.uploaded,
            )
            self.db.add(video)
            self.db.flush()
            record_structured_audit_log(
                self.db,
                workspace_id=workspace_id,
                user_id=owner_user_id,
                action="video_upload_succeeded",
                target_type="video",
                target_id=str(video.id),
                payload={"original_file_name": safe_name},
            )
            self.db.commit()
            self.db.refresh(video)
            return self._serialize_videos([video])[0]
        except Exception as exc:
            self.db.rollback()
            record_structured_audit_log(
                self.db,
                workspace_id=workspace_id,
                user_id=owner_user_id,
                action="video_upload_failed",
                target_type="video_upload",
                target_id=str(video_id),
                status="failed",
                message=str(exc),
                payload={"original_file_name": safe_name},
            )
            self.db.commit()
            raise

    def process_video(self, video_id: str, *, regenerate_metadata_only: bool = False) -> None:
        video = self.db.scalar(select(Video).where(Video.id == uuid.UUID(video_id), Video.deleted_at.is_(None)))
        if video is None:
            raise ApiError(404, "video_not_found", "Video not found.")

        transcript = self.db.scalar(
            select(VideoTranscript).where(VideoTranscript.video_id == video.id)
        )

        if not regenerate_metadata_only or transcript is None:
            video.status = VideoLifecycleStatus.transcribing
            video.processing_error_code = None
            video.processing_error_message = None
            self.db.commit()

            source_bytes = self.storage.read_bytes(video.storage_bucket, video.storage_object_name)
            audio_bytes = self._extract_audio_bytes(source_bytes, video.original_file_name)
            words = transcribe_audio_bytes(audio_bytes, settings=self.settings)
            transcript_text = " ".join(word.word for word in words).strip()
            if not transcript_text:
                raise AdapterError(
                    "deterministic_input",
                    "transcript_empty",
                    "Whisper did not detect spoken audio in the uploaded video.",
                )
            words_payload = [
                {
                    "word": word.word,
                    "start_ms": int(word.start * 1000),
                    "end_ms": int(word.end * 1000),
                }
                for word in words
            ]
            if transcript is None:
                transcript = VideoTranscript(
                    workspace_id=video.workspace_id,
                    video_id=video.id,
                    transcript_text=transcript_text,
                    language_code="unknown",
                    word_count=len(words_payload),
                    words_payload=words_payload,
                    whisper_model_size="small",
                )
                self.db.add(transcript)
            else:
                transcript.transcript_text = transcript_text
                transcript.language_code = "unknown"
                transcript.word_count = len(words_payload)
                transcript.words_payload = words_payload
                transcript.whisper_model_size = "small"
            video.transcript_ready_at = datetime.now(UTC)
            self.db.commit()

        assert transcript is not None
        routing_service = RoutingService(self.db, self.settings)
        text_provider, decision = routing_service.build_text_provider_for_workspace(video.workspace_id)
        metadata_payload = text_provider.generate_video_metadata(
            transcript_text=transcript.transcript_text,
            video_context={
                "original_file_name": video.original_file_name,
                "duration_ms": video.duration_ms,
                "width": video.width,
                "height": video.height,
            },
        )
        title_options = [
            str(item).strip()[:100]
            for item in list(metadata_payload.get("title_options") or [])
            if str(item).strip()
        ][:5]
        preferred_title = str(
            metadata_payload.get("recommended_title")
            or (title_options[0] if title_options else video.original_file_name)
        ).strip()[:100]
        try:
            title, description, tags = self.youtube_integration.sanitize_metadata(
                title=preferred_title,
                description=str(metadata_payload.get("description") or ""),
                tags=[str(item) for item in list(metadata_payload.get("tags") or [])],
            )
        except ApiError as exc:
            raise AdapterError("deterministic_input", exc.code, exc.message) from exc
        if not title_options:
            title_options = [title]

        version = VideoMetadataVersion(
            workspace_id=video.workspace_id,
            video_id=video.id,
            transcript_id=transcript.id,
            version_number=self._next_metadata_version_number(video.id),
            source_type=VideoMetadataSource.generated,
            provider_name=decision.provider_name,
            provider_model=decision.provider_model,
            title_options=title_options,
            recommended_title=title,
            title=title,
            description=description,
            tags=tags,
            hook_summary=(str(metadata_payload.get("hook_summary") or "").strip() or None),
            raw_response_payload=dict(metadata_payload or {}),
            is_approved=False,
        )
        self.db.add(version)
        video.metadata_ready_at = datetime.now(UTC)
        if video.status not in {VideoLifecycleStatus.scheduled, VideoLifecycleStatus.publishing, VideoLifecycleStatus.published}:
            video.status = VideoLifecycleStatus.metadata_ready
        video.processing_error_code = None
        video.processing_error_message = None
        self.db.commit()

    def mark_processing_failed(self, video_id: str, error: AdapterError) -> None:
        video = self.db.scalar(select(Video).where(Video.id == uuid.UUID(video_id)))
        if video is None:
            return
        video.status = VideoLifecycleStatus.failed
        video.processing_error_code = error.code
        video.processing_error_message = error.message
        self.db.commit()

    def mark_processing_retry(self, video_id: str, error: AdapterError) -> None:
        video = self.db.scalar(select(Video).where(Video.id == uuid.UUID(video_id)))
        if video is None:
            return
        video.status = VideoLifecycleStatus.transcribing
        video.processing_error_code = error.code
        video.processing_error_message = error.message
        self.db.commit()

    def approve_metadata(
        self,
        auth: AuthContext,
        *,
        video_id: str,
        metadata_version_id: str | None,
        title: str,
        description: str,
        tags: list[str],
        hook_summary: str | None,
        youtube_account_id: str | None,
    ) -> dict[str, object]:
        video = self._get_owned_video(auth, video_id)
        if video.status in {VideoLifecycleStatus.scheduled, VideoLifecycleStatus.publishing, VideoLifecycleStatus.published}:
            raise ApiError(
                409,
                "video_metadata_locked",
                "Metadata can only be approved before the video is scheduled or published.",
            )
        base_version = None
        if metadata_version_id:
            base_version = self.db.scalar(
                select(VideoMetadataVersion).where(
                    VideoMetadataVersion.id == uuid.UUID(metadata_version_id),
                    VideoMetadataVersion.video_id == video.id,
                )
            )
        if base_version is None:
            base_version = self.db.scalar(
                select(VideoMetadataVersion)
                .where(VideoMetadataVersion.video_id == video.id)
                .order_by(VideoMetadataVersion.version_number.desc())
            )
        if base_version is None:
            raise ApiError(422, "video_metadata_missing", "Generate metadata before approving it.")

        normalized_title, normalized_description, normalized_tags = self.youtube_integration.sanitize_metadata(
            title=title,
            description=description,
            tags=tags,
        )
        if youtube_account_id:
            account = YouTubeAccountService(self.db, self.settings).get_owned_account(
                workspace_id=auth.workspace_id,
                owner_user_id=auth.user_id,
                youtube_account_id=youtube_account_id,
            )
            video.youtube_account_id = account.id

        versions = self.db.scalars(
            select(VideoMetadataVersion).where(VideoMetadataVersion.video_id == video.id)
        ).all()
        for version in versions:
            version.is_approved = False
            version.approved_at = None

        approved = VideoMetadataVersion(
            workspace_id=video.workspace_id,
            video_id=video.id,
            transcript_id=base_version.transcript_id,
            created_by_user_id=uuid.UUID(auth.user_id),
            version_number=self._next_metadata_version_number(video.id),
            source_type=VideoMetadataSource.manual,
            provider_name=base_version.provider_name,
            provider_model=base_version.provider_model,
            title_options=list(base_version.title_options or []),
            recommended_title=base_version.recommended_title,
            title=normalized_title,
            description=normalized_description,
            tags=normalized_tags,
            hook_summary=hook_summary,
            raw_response_payload={"approved_from_version_id": str(base_version.id)},
            is_approved=True,
            approved_at=datetime.now(UTC),
        )
        self.db.add(approved)
        self.db.flush()
        video.approved_metadata_version_id = approved.id
        video.status = VideoLifecycleStatus.metadata_ready
        self.db.commit()
        self.db.refresh(video)
        return self.get_video(auth, str(video.id))

    def _serialize_videos(self, videos: list[Video]) -> list[dict[str, object]]:
        if not videos:
            return []
        video_ids = [video.id for video in videos]
        transcripts = self.db.scalars(
            select(VideoTranscript).where(VideoTranscript.video_id.in_(video_ids))
        ).all()
        transcripts_by_video = {item.video_id: item for item in transcripts}

        metadata_versions = self.db.scalars(
            select(VideoMetadataVersion)
            .where(VideoMetadataVersion.video_id.in_(video_ids))
            .order_by(VideoMetadataVersion.version_number.desc())
        ).all()
        versions_by_video: dict[uuid.UUID, list[VideoMetadataVersion]] = defaultdict(list)
        for item in metadata_versions:
            versions_by_video[item.video_id].append(item)

        return [
            video_to_dict(
                video,
                transcript=transcripts_by_video.get(video.id),
                metadata_versions=versions_by_video.get(video.id, []),
            )
            for video in videos
        ]

    def _next_metadata_version_number(self, video_id: uuid.UUID) -> int:
        versions = self.db.scalars(
            select(VideoMetadataVersion.version_number).where(VideoMetadataVersion.video_id == video_id)
        ).all()
        return (max(versions) if versions else 0) + 1

    def _get_owned_video(self, auth: AuthContext, video_id: str) -> Video:
        video = self.db.scalar(
            select(Video).where(
                Video.id == uuid.UUID(video_id),
                Video.workspace_id == uuid.UUID(auth.workspace_id),
                Video.owner_user_id == uuid.UUID(auth.user_id),
                Video.deleted_at.is_(None),
            )
        )
        if video is None:
            raise ApiError(404, "video_not_found", "Video not found.")
        return video

    def _extract_audio_bytes(self, source_bytes: bytes, source_file_name: str) -> bytes:
        runner = FFmpegRunner(self.settings)
        if not runner.available():
            raise AdapterError(
                "transient",
                "ffmpeg_unavailable",
                "FFmpeg is required to extract audio for Whisper transcription.",
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            input_name = f"input{Path(source_file_name).suffix or '.mp4'}"
            (workdir / input_name).write_bytes(source_bytes)
            try:
                runner.run(
                    "ffmpeg",
                    ["-y", "-i", input_name, "-vn", "-ac", "1", "-ar", "16000", "audio.wav"],
                    workdir=workdir,
                )
            except FFmpegError as exc:
                raise AdapterError(
                    "transient",
                    "audio_extraction_failed",
                    f"FFmpeg could not extract audio from the uploaded video: {exc}",
                ) from exc
            return (workdir / "audio.wav").read_bytes()
