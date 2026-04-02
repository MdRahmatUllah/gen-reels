from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reels_generation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_default_queue="planning",
    task_always_eager=settings.celery_task_always_eager,
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    task_routes={
        "planning.bootstrap_project": {"queue": "planning"},
        "planning.generate_ideas": {"queue": "planning"},
        "planning.generate_script": {"queue": "planning"},
        "planning.generate_scene_plan": {"queue": "planning"},
        "planning.generate_prompt_pairs": {"queue": "planning"},
        "planning.generate_series_run": {"queue": "planning"},
        "planning.expire_stale_jobs": {"queue": "planning"},
        "render.expire_stale_jobs": {"queue": "maintenance"},
        "render.execute_job": {"queue": "frame"},
        "remix.execute_job": {"queue": "frame"},
        "billing.reconcile_usage": {"queue": "maintenance"},
        "workspace.refresh_local_workers": {"queue": "maintenance"},
        "notifications.deliver_email": {"queue": "notifications"},
        "notifications.deliver_webhook": {"queue": "notifications"},
        "maintenance.process_frame_pair_review_timeouts": {"queue": "maintenance"},
        "maintenance.cleanup_expired_assets": {"queue": "maintenance"},
        "maintenance.archive_old_quarantine_records": {"queue": "maintenance"},
        "maintenance.refresh_provider_health": {"queue": "maintenance"},
    },
    beat_schedule={
        "expire-stale-planning-jobs": {
            "task": "planning.expire_stale_jobs",
            "schedule": crontab(minute="*/15"),
        },
        "expire-stale-render-jobs": {
            "task": "render.expire_stale_jobs",
            "schedule": crontab(minute="*/15"),
        },
        "reconcile-usage-ledger": {
            "task": "billing.reconcile_usage",
            "schedule": crontab(minute="0"),
        },
        "refresh-local-workers": {
            "task": "workspace.refresh_local_workers",
            "schedule": crontab(minute="*/2"),
        },
        "process-frame-pair-review-timeouts": {
            "task": "maintenance.process_frame_pair_review_timeouts",
            "schedule": crontab(minute="0"),
        },
        "cleanup-expired-assets": {
            "task": "maintenance.cleanup_expired_assets",
            "schedule": crontab(hour="2", minute="0"),
        },
        "archive-old-quarantine-records": {
            "task": "maintenance.archive_old_quarantine_records",
            "schedule": crontab(day_of_week="0", hour="3", minute="0"),
        },
        "refresh-provider-health": {
            "task": "maintenance.refresh_provider_health",
            "schedule": crontab(minute="*/5"),
        },
    },
)
celery_app.autodiscover_tasks(["app.workers"])
