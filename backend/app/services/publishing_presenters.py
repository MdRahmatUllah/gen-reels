from __future__ import annotations

from datetime import datetime

from app.models.youtube import (
    PublishJob,
    PublishSchedule,
    Video,
    VideoMetadataVersion,
    VideoTranscript,
    YouTubeAccount,
)


def youtube_account_to_dict(account: YouTubeAccount) -> dict[str, object]:
    return {
        "id": account.id,
        "google_account_email": account.google_account_email,
        "channel_id": account.channel_id,
        "channel_title": account.channel_title,
        "channel_handle": account.channel_handle,
        "is_default": account.is_default,
        "token_expiry_at": account.token_expiry_at,
        "connected_at": account.connected_at,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def publish_schedule_to_dict(
    schedule: PublishSchedule,
    *,
    next_available_slots_utc: list[datetime] | None = None,
) -> dict[str, object]:
    return {
        "id": schedule.id,
        "youtube_account_id": schedule.youtube_account_id,
        "timezone_name": schedule.timezone_name,
        "slots_local": list(schedule.slots_local or []),
        "is_active": schedule.is_active,
        "next_available_slots_utc": next_available_slots_utc or [],
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
    }


def video_transcript_to_dict(transcript: VideoTranscript) -> dict[str, object]:
    return {
        "id": transcript.id,
        "language_code": transcript.language_code,
        "word_count": transcript.word_count,
        "transcript_text": transcript.transcript_text,
        "whisper_model_size": transcript.whisper_model_size,
        "created_at": transcript.created_at,
        "updated_at": transcript.updated_at,
    }


def video_metadata_version_to_dict(version: VideoMetadataVersion) -> dict[str, object]:
    return {
        "id": version.id,
        "video_id": version.video_id,
        "version_number": version.version_number,
        "source_type": version.source_type.value,
        "provider_name": version.provider_name,
        "provider_model": version.provider_model,
        "title_options": list(version.title_options or []),
        "recommended_title": version.recommended_title,
        "title": version.title,
        "description": version.description,
        "tags": list(version.tags or []),
        "hook_summary": version.hook_summary,
        "is_approved": version.is_approved,
        "approved_at": version.approved_at,
        "created_at": version.created_at,
        "updated_at": version.updated_at,
    }


def video_to_dict(
    video: Video,
    *,
    transcript: VideoTranscript | None,
    metadata_versions: list[VideoMetadataVersion],
) -> dict[str, object]:
    approved = next((item for item in metadata_versions if item.id == video.approved_metadata_version_id), None)
    return {
        "id": video.id,
        "youtube_account_id": video.youtube_account_id,
        "approved_metadata_version_id": video.approved_metadata_version_id,
        "original_file_name": video.original_file_name,
        "content_type": video.content_type,
        "size_bytes": video.size_bytes,
        "duration_ms": video.duration_ms,
        "width": video.width,
        "height": video.height,
        "status": video.status.value,
        "scheduled_publish_at": video.scheduled_publish_at,
        "published_at": video.published_at,
        "youtube_video_id": video.youtube_video_id,
        "processing_error_code": video.processing_error_code,
        "processing_error_message": video.processing_error_message,
        "created_at": video.created_at,
        "updated_at": video.updated_at,
        "transcript": video_transcript_to_dict(transcript) if transcript else None,
        "metadata_versions": [video_metadata_version_to_dict(item) for item in metadata_versions],
        "approved_metadata_version": video_metadata_version_to_dict(approved) if approved else None,
    }


def publish_job_to_dict(
    job: PublishJob,
    *,
    original_file_name: str | None = None,
    channel_title: str | None = None,
) -> dict[str, object]:
    return {
        "id": job.id,
        "video_id": job.video_id,
        "youtube_account_id": job.youtube_account_id,
        "metadata_version_id": job.metadata_version_id,
        "publish_mode": job.publish_mode.value,
        "visibility": job.visibility.value,
        "scheduled_publish_at": job.scheduled_publish_at,
        "status": job.status.value,
        "queued_at": job.queued_at,
        "started_at": job.started_at,
        "published_at": job.published_at,
        "failed_at": job.failed_at,
        "cancelled_at": job.cancelled_at,
        "youtube_video_id": job.youtube_video_id,
        "youtube_video_url": job.youtube_video_url,
        "attempt_count": job.attempt_count,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "last_progress_percent": job.last_progress_percent,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "original_file_name": original_file_name,
        "channel_title": channel_title,
    }
