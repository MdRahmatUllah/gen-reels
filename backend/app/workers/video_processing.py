from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.errors import AdapterError
from app.db.session import get_session_factory
from app.services.video_service import VideoService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="video.process_upload")
def process_uploaded_video_task(self, video_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = VideoService(session, settings)
    try:
        service.process_video(video_id, regenerate_metadata_only=False)
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_processing_retry(video_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_processing_failed(video_id, error)
    except Exception as exc:  # pragma: no cover - defensive worker guard
        logger.exception("unexpected_video_processing_failure video_id=%s", video_id)
        error = AdapterError("internal", "video_processing_unexpected_error", str(exc))
        service.mark_processing_failed(video_id, error)
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=2, name="video.generate_metadata")
def regenerate_video_metadata_task(self, video_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = VideoService(session, settings)
    try:
        service.process_video(video_id, regenerate_metadata_only=True)
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_processing_retry(video_id, error)
            raise self.retry(exc=error, countdown=20 * (2**self.request.retries))
        service.mark_processing_failed(video_id, error)
    except Exception as exc:  # pragma: no cover - defensive worker guard
        logger.exception("unexpected_video_metadata_failure video_id=%s", video_id)
        error = AdapterError("internal", "video_metadata_unexpected_error", str(exc))
        service.mark_processing_failed(video_id, error)
        raise
    finally:
        session.close()
