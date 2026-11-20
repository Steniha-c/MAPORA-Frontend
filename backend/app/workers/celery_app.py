"""Celery worker configuration."""

import os
import socket
from urllib.parse import urlparse
from celery import Celery

from app.core.config import settings


def _is_broker_listening(url_str: str, timeout: float = 0.2) -> bool:
    """Fast probe checking whether Celery broker is active."""
    try:
        parsed = urlparse(url_str)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


raw_broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
raw_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

if _is_broker_listening(raw_broker, timeout=0.2):
    broker_url = raw_broker
    backend_url = raw_backend
else:
    # Resilient fallback for local development without running Redis
    broker_url = "memory://"
    backend_url = "cache+memory://"

celery_app = Celery(
    "mapora_worker",
    broker=broker_url,
    backend=backend_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=1.0,
    broker_transport_options={
        "max_retries": 1,
        "socket_timeout": 1.0,
        "socket_connect_timeout": 1.0,
    },
    result_backend_transport_options={
        "max_retries": 1,
        "socket_timeout": 1.0,
        "socket_connect_timeout": 1.0,
    },
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
