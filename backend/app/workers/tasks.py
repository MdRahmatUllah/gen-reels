from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.errors import AdapterError
from app.db.session import get_session_factory
from app.integrations.azure import build_moderation_provider, build_text_provider
from app.integrations.media import (
    build_image_provider,
    build_music_provider,
    build_speech_provider,
    build_video_provider,
)
from app.integrations.storage import build_storage_client
from app.services.content_planning_service import ContentPlanningService
from app.services.generation_service import GenerationService
from app.services.render_service import RenderService
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


@celery_app.task(bind=True, max_retries=3, name="planning.generate_scene_plan")
def generate_scene_plan_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = ContentPlanningService(session, settings)
    try:
        service.execute_scene_plan_job(job_id, build_text_provider(settings))
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_job_retry(job_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_job_failed(job_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_scene_plan_task_failure job_id=%s", job_id)
        service.mark_job_failed(job_id, AdapterError("internal", "unexpected_error", str(exc)))
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3, name="planning.generate_prompt_pairs")
def generate_prompt_pairs_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = ContentPlanningService(session, settings)
    try:
        service.execute_prompt_pair_job(job_id, build_text_provider(settings))
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_job_retry(job_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_job_failed(job_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_prompt_pair_task_failure job_id=%s", job_id)
        service.mark_job_failed(job_id, AdapterError("internal", "unexpected_error", str(exc)))
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=2, name="render.execute_job")
def execute_render_job_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = RenderService(session, settings, build_storage_client(settings))
    try:
        service.execute_render_job(
            job_id,
            image_provider=build_image_provider(settings),
            video_provider=build_video_provider(settings),
            speech_provider=build_speech_provider(settings),
            music_provider=build_music_provider(settings),
            moderation_provider=build_moderation_provider(settings),
        )
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_job_retry(job_id, error)
            raise self.retry(exc=error, countdown=60 * (2**self.request.retries))
        service.mark_job_failed(job_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_render_task_failure job_id=%s", job_id)
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
