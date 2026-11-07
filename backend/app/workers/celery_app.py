"""Celery worker configuration."""

import os
from celery import Celery

from app.core.config import settings

broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
backend_url = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "mapora_worker",
    broker=broker_url,
    backend=backend_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minute hard timeout
    task_soft_time_limit=1500,  # 25 minute soft timeout
    worker_concurrency=int(os.environ.get("CELERY_CONCURRENCY", "2")),
)
