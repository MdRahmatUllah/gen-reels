from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.errors import AdapterError
from app.db.session import get_session_factory
from app.integrations.media import build_music_provider
from app.integrations.storage import build_storage_client
from app.services.content_planning_service import ContentPlanningService
from app.services.generation_service import GenerationService
from app.services.billing_service import BillingService
from app.services.notification_service import NotificationService
from app.services.quick_start_service import QuickStartService
from app.services.series_generation_service import SeriesGenerationService
from app.services.series_video_service import SeriesVideoService
from app.services.routing_service import RoutingService
from app.services.remix_service import RemixService as RemixServiceClass
from app.services.render_service import RenderService
from app.services.workspace_service import WorkspaceService
from app.workers.celery_app import celery_app
from app.workers import video_processing as _video_processing  # noqa: F401
from app.workers import youtube_publish as _youtube_publish  # noqa: F401

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="planning.generate_ideas")
def generate_ideas_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = GenerationService(session, settings)
    try:
        service.execute_idea_job(job_id)
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
        service.execute_script_job(job_id)
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
        service.execute_scene_plan_job(job_id)
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
        service.execute_prompt_pair_job(job_id)
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


@celery_app.task(bind=True, max_retries=3, name="planning.bootstrap_project")
def bootstrap_project_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = QuickStartService(session, settings)
    try:
        service.execute_quick_start_job(job_id)
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_quick_start_retry(job_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_quick_start_failed(job_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_quick_start_task_failure job_id=%s", job_id)
        service.mark_quick_start_failed(job_id, AdapterError("internal", "unexpected_error", str(exc)))
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3, name="planning.generate_series_run")
def generate_series_run_task(self, run_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = SeriesGenerationService(session, settings)
    try:
        service.execute_series_run(run_id)
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_series_run_retry(run_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_series_run_failed(run_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_series_run_task_failure run_id=%s", run_id)
        service.mark_series_run_failed(run_id, AdapterError("internal", "unexpected_error", str(exc)))
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3, name="planning.generate_series_video_run")
def generate_series_video_run_task(self, run_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = SeriesVideoService(session, settings)
    try:
        service.execute_video_run(run_id)
    except AdapterError as error:
        if error.category == "transient" and self.request.retries < self.max_retries:
            service.mark_video_run_retry(run_id, error)
            raise self.retry(exc=error, countdown=30 * (2**self.request.retries))
        service.mark_video_run_failed(run_id, error)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("unexpected_series_video_run_task_failure run_id=%s", run_id)
        service.mark_video_run_failed(run_id, AdapterError("internal", "unexpected_error", str(exc)))
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=2, name="render.execute_job")
def execute_render_job_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    service = RenderService(session, settings, build_storage_client(settings))
    try:
        service.execute_render_job(job_id, music_provider=build_music_provider(settings))
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


@celery_app.task(bind=True, max_retries=1, name="remix.execute_job")
def execute_remix_job_task(self, job_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        RemixServiceClass(session, settings).execute_job(job_id)
    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_remix_task_failure job_id=%s", job_id)
        raise
    finally:
        session.close()


@celery_app.task(name="notifications.deliver_email")
def deliver_notification_email_task(notification_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        NotificationService(session, settings).deliver_notification_email(notification_id)
    finally:
        session.close()


@celery_app.task(name="notifications.deliver_webhook")
def deliver_webhook_delivery_task(delivery_id: str) -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        WorkspaceService(session, settings).deliver_webhook_delivery(delivery_id)
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


@celery_app.task(name="render.expire_stale_jobs")
def expire_stale_render_jobs() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return RenderService(session, settings, build_storage_client(settings)).expire_stale_render_jobs()
    finally:
        session.close()


@celery_app.task(name="billing.reconcile_usage")
def reconcile_usage() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return BillingService(session, settings).reconcile_usage_entries()
    finally:
        session.close()


@celery_app.task(name="workspace.refresh_local_workers")
def refresh_local_workers() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return RoutingService(session, settings).refresh_worker_statuses()
    finally:
        session.close()


@celery_app.task(name="maintenance.process_frame_pair_review_timeouts")
def process_frame_pair_review_timeouts() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return RenderService(session, settings, build_storage_client(settings)).process_frame_pair_review_timeouts()
    finally:
        session.close()


@celery_app.task(name="maintenance.cleanup_expired_assets")
def cleanup_expired_assets() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return RenderService(session, settings, build_storage_client(settings)).cleanup_expired_assets()
    finally:
        session.close()


@celery_app.task(name="maintenance.archive_old_quarantine_records")
def archive_old_quarantine_records() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return RenderService(session, settings, build_storage_client(settings)).archive_old_quarantine_records()
    finally:
        session.close()


@celery_app.task(name="maintenance.refresh_provider_health")
def refresh_provider_health() -> int:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        return RenderService(session, settings, build_storage_client(settings)).refresh_provider_health()
    finally:
        session.close()
