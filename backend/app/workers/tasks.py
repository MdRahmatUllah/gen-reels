from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.errors import AdapterError
from app.db.session import get_session_factory
from app.integrations.azure import build_text_provider
from app.services.generation_service import GenerationService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="planning.generate_ideas")
def generate_ideas_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = GenerationService(session, settings)
    try:
        service.execute_idea_job(job_id, build_text_provider(settings))
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_job_retry(job_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_job_failed(job_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_idea_task_failure job_id=%s", job_id)
        service.mark_job_failed(job_id, AdapterError("internal", "unexpected_error", str(exc)))
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3, name="planning.generate_script")
def generate_script_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = GenerationService(session, settings)
    try:
        service.execute_script_job(job_id, build_text_provider(settings))
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_job_retry(job_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_job_failed(job_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_script_task_failure job_id=%s", job_id)
        service.mark_job_failed(job_id, AdapterError("internal", "unexpected_error", str(exc)))
        raise
    finally:
        session.close()


@celery_app.task(name="planning.expire_stale_jobs")
def expire_stale_jobs() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return GenerationService(session, settings).expire_stale_jobs()
    finally:
        session.close()
