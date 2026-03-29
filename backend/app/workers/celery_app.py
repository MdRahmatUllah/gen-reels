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
        "planning.generate_ideas": {"queue": "planning"},
        "planning.generate_script": {"queue": "planning"},
        "planning.generate_scene_plan": {"queue": "planning"},
        "planning.generate_prompt_pairs": {"queue": "planning"},
        "planning.expire_stale_jobs": {"queue": "planning"},
        "render.expire_stale_jobs": {"queue": "render"},
        "render.execute_job": {"queue": "render"},
        "billing.reconcile_usage": {"queue": "planning"},
        "workspace.refresh_local_workers": {"queue": "planning"},
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
    },
)
celery_app.autodiscover_tasks(["app.workers"])
