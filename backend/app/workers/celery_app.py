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
    beat_schedule={
        "expire-stale-planning-jobs": {
            "task": "planning.expire_stale_jobs",
            "schedule": crontab(minute="*/15"),
        }
    },
)
celery_app.autodiscover_tasks(["app.workers"])
