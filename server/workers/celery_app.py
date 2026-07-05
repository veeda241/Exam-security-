"""Celery application and worker task registry."""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))

celery_app = Celery(
    "examguard",
    broker=REDIS_URL,
    backend=os.getenv("CELERY_RESULT_BACKEND", REDIS_URL),
    include=[
        "workers.face_worker",
        "workers.object_worker",
        "workers.gaze_worker",
        "workers.ocr_worker",
        "workers.nlp_worker",
        "workers.report_worker",
        "workers.cleanup_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_routes={
        "workers.face_worker.*": {"queue": "face"},
        "workers.object_worker.*": {"queue": "object"},
        "workers.gaze_worker.*": {"queue": "gaze"},
        "workers.ocr_worker.*": {"queue": "ocr"},
        "workers.nlp_worker.*": {"queue": "nlp"},
        "workers.report_worker.*": {"queue": "report"},
        "workers.cleanup_worker.*": {"queue": "default"},
    },
    beat_schedule={
        "retention-cleanup-daily": {
            "task": "workers.cleanup_worker.run_retention_cleanup",
            "schedule": crontab(hour=3, minute=0),
        },
        "stale-session-cleanup": {
            "task": "workers.cleanup_worker.terminate_stale_sessions",
            "schedule": crontab(minute="*/30"),
        },
    },
)
