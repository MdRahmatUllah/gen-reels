from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.errors import AdapterError
from app.db.session import get_session_factory
from app.services.publish_job_service import PublishJobService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=5, name="youtube.publish_job")
def publish_job_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = PublishJobService(session, settings)
    try:
        service.execute_publish_job(job_id)
    except AdapterError as error:
        attempt_count = self.request.retries + 1
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_job_retry(job_id, error, attempt_count)
            raise self.retry(exc=error, countdown=60 * (2**self.request.retries))
        service.mark_job_failed(job_id, error, attempt_count)
    except Exception as exc:  # pragma: no cover - defensive worker guard
        logger.exception("unexpected_youtube_publish_failure job_id=%s", job_id)
        error = AdapterError("internal", "youtube_publish_unexpected_error", str(exc))
        service.mark_job_failed(job_id, error, self.request.retries + 1)
        raise
    finally:
        session.close()


@celery_app.task(name="youtube.enqueue_due_jobs")
def enqueue_due_publish_jobs_task() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return PublishJobService(session, settings).enqueue_due_jobs()
    finally:
        session.close()
